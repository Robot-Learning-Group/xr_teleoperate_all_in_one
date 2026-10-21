#!/usr/bin/env python3
"""Expose an OAK color camera as a UVC webcam."""

import argparse
import time
from pathlib import Path

import depthai as dai

try:
    import yaml
except ModuleNotFoundError:
    yaml = None

PROFILES = {
    "rgb-full-fov": {
        "sensor_resolution": "12mp",
        "width": 2028,
        "height": 1520,
        "isp_scale": "1/2",
    },
    "rgb-full-fov-low": {
        "sensor_resolution": "12mp",
        "width": 1014,
        "height": 760,
        "isp_scale": "1/4",
    },
    "legacy-720p": {
        "sensor_resolution": "1080p",
        "width": 1280,
        "height": 720,
        "isp_scale": None,
    },
}

SENSOR_RESOLUTIONS = {
    "1080p": dai.ColorCameraProperties.SensorResolution.THE_1080_P,
    "4k": dai.ColorCameraProperties.SensorResolution.THE_4_K,
    "12mp": dai.ColorCameraProperties.SensorResolution.THE_12_MP,
}

SENSOR_SIZES = {
    "1080p": (1920, 1080),
    "4k": (3840, 2160),
    "12mp": (4056, 3040),
}

ANTI_BANDING_MODES = {
    "auto": dai.CameraControl.AntiBandingMode.AUTO,
    "50hz": dai.CameraControl.AntiBandingMode.MAINS_50_HZ,
    "60hz": dai.CameraControl.AntiBandingMode.MAINS_60_HZ,
    "off": dai.CameraControl.AntiBandingMode.OFF,
}

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "oak_uvc_config.yaml"
DEFAULT_OAK_UVC_CONFIG = {
    "profile": "rgb-full-fov-low",
    "width": None,
    "height": None,
    "fps": 30.0,
    "sensor_resolution": None,
    "isp_scale": None,
    "fov_scale": 1.0,
    "ae_compensation": -3,
    "ae_max_exposure_us": None,
    "anti_banding": "auto",
    "manual_exposure_us": None,
    "manual_iso": None,
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the OAK UVC config YAML.",
    )
    return parser.parse_args()


def _parse_isp_scale(value):
    if value is None or str(value).lower() == "none":
        return None
    try:
        numerator, denominator = str(value).split("/", 1)
        numerator = int(numerator)
        denominator = int(denominator)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--isp-scale must be NUM/DEN, e.g. 1/2") from exc
    if numerator <= 0 or denominator <= 0:
        raise argparse.ArgumentTypeError("--isp-scale numerator and denominator must be positive")
    return numerator, denominator


def _format_isp_scale(isp_scale):
    return "none" if isp_scale is None else f"{isp_scale[0]}/{isp_scale[1]}"


def _scaled_sensor_size(sensor_resolution, isp_scale):
    sensor_width, sensor_height = SENSOR_SIZES[sensor_resolution]
    if isp_scale is None:
        return sensor_width, sensor_height
    numerator, denominator = isp_scale
    return sensor_width * numerator // denominator, sensor_height * numerator // denominator


def _validate_isp_scale(sensor_resolution, isp_scale):
    if isp_scale is None:
        return
    sensor_width, sensor_height = SENSOR_SIZES[sensor_resolution]
    numerator, denominator = isp_scale
    if (sensor_width * numerator) % denominator != 0 or (sensor_height * numerator) % denominator != 0:
        raise ValueError(
            "oak_uvc.isp_scale must produce integer ISP dimensions for the selected sensor: "
            f"sensor={sensor_width}x{sensor_height}, isp_scale={_format_isp_scale(isp_scale)}"
        )
    scaled_width, scaled_height = _scaled_sensor_size(sensor_resolution, isp_scale)
    if scaled_width % 2 != 0 or scaled_height % 2 != 0:
        raise ValueError(
            "oak_uvc.isp_scale must produce even ISP dimensions for NV12/UVC output: "
            f"scaled={scaled_width}x{scaled_height}"
        )


def _validate_output_size(width, height):
    if width <= 0 or height <= 0:
        raise ValueError("oak_uvc width and height must be positive")
    if width % 2 != 0 or height % 2 != 0:
        raise ValueError("oak_uvc width and height must be even for NV12/UVC output")


def _validate_source_covers_output(width, height, sensor_resolution, isp_scale):
    source_width, source_height = _scaled_sensor_size(sensor_resolution, isp_scale)
    if source_width < width or source_height < height:
        raise ValueError(
            "oak_uvc output is larger than the selected sensor/ISP source: "
            f"source={source_width}x{source_height}, output={width}x{height}"
        )


def _parse_scalar(value):
    value = value.strip()
    if value in ("", "null", "None", "~"):
        return None
    if value in ("true", "True"):
        return True
    if value in ("false", "False"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value.strip("'\"")


def _load_yaml_mapping(config_path):
    text = config_path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Config file must contain a mapping: {config_path}")
        return data

    data = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        if ":" not in line:
            raise ValueError(f"Unsupported config line in {config_path}: {line}")
        key, value = line.split(":", 1)
        data[key.strip()] = _parse_scalar(value)
    return data


def _load_oak_uvc_config(config_path):
    config = DEFAULT_OAK_UVC_CONFIG.copy()
    try:
        data = _load_yaml_mapping(config_path)
    except FileNotFoundError:
        print(f"Config file not found: {config_path}. Using built-in defaults.")
        return config

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a mapping: {config_path}")

    for key in config:
        if key in data:
            config[key] = data[key]

    return config


def _validate_config(config):
    if config["profile"] not in PROFILES:
        raise ValueError(f"oak_uvc.profile must be one of {sorted(PROFILES)}")
    if config["sensor_resolution"] is not None and config["sensor_resolution"] not in SENSOR_RESOLUTIONS:
        raise ValueError(f"oak_uvc.sensor_resolution must be one of {sorted(SENSOR_RESOLUTIONS)}")
    if config["anti_banding"] not in ANTI_BANDING_MODES:
        raise ValueError(f"oak_uvc.anti_banding must be one of {sorted(ANTI_BANDING_MODES)}")
    fov_scale = float(config["fov_scale"])
    if not 0.5 <= fov_scale <= 1.0:
        raise ValueError("oak_uvc.fov_scale must be between 0.5 and 1.0")
    if not -9 <= int(config["ae_compensation"]) <= 9:
        raise ValueError("oak_uvc.ae_compensation must be between -9 and 9")
    if config["ae_max_exposure_us"] is not None and int(config["ae_max_exposure_us"]) <= 0:
        raise ValueError("oak_uvc.ae_max_exposure_us must be positive")
    if (config["manual_exposure_us"] is None) != (config["manual_iso"] is None):
        raise ValueError("oak_uvc.manual_exposure_us and oak_uvc.manual_iso must be specified together")
    if config["manual_exposure_us"] is not None and int(config["manual_exposure_us"]) <= 0:
        raise ValueError("oak_uvc.manual_exposure_us must be positive")
    if config["manual_iso"] is not None and int(config["manual_iso"]) <= 0:
        raise ValueError("oak_uvc.manual_iso must be positive")


def main():
    args = parse_args()
    oak_config = _load_oak_uvc_config(args.config)
    _validate_config(oak_config)
    profile = PROFILES[oak_config["profile"]]
    width = int(oak_config["width"] or profile["width"])
    height = int(oak_config["height"] or profile["height"])
    fps = float(oak_config["fps"])
    _validate_output_size(width, height)
    if fps <= 0:
        raise ValueError("oak_uvc.fps must be positive")
    sensor_resolution = oak_config["sensor_resolution"] or profile["sensor_resolution"]
    fov_scale = float(oak_config["fov_scale"])
    if oak_config["isp_scale"] is not None:
        isp_scale = _parse_isp_scale(oak_config["isp_scale"])
    else:
        isp_scale = _parse_isp_scale(profile["isp_scale"])

    _validate_isp_scale(sensor_resolution, isp_scale)
    _validate_source_covers_output(width, height, sensor_resolution, isp_scale)

    # Keep the UVC device at the selected camera/profile FOV. Cropping is applied
    # in teleimager after OpenCV reads the UVC frame, avoiding DepthAI ImageManip
    # crop discontinuities observed around fov_scale=0.89.

    pipeline = dai.Pipeline()
    color = pipeline.createColorCamera()
    uvc = pipeline.createUVC()

    color.setBoardSocket(dai.CameraBoardSocket.CAM_A)
    color.setResolution(SENSOR_RESOLUTIONS[sensor_resolution])
    if isp_scale is not None:
        color.setIspScale(*isp_scale)
    color.setVideoSize(width, height)
    color.setFps(fps)
    color.setInterleaved(False)
    color.initialControl.setAntiBandingMode(ANTI_BANDING_MODES[oak_config["anti_banding"]])
    if oak_config["manual_exposure_us"] is not None:
        color.initialControl.setManualExposure(int(oak_config["manual_exposure_us"]), int(oak_config["manual_iso"]))
    else:
        color.initialControl.setAutoExposureCompensation(int(oak_config["ae_compensation"]))
        if oak_config["ae_max_exposure_us"] is not None:
            color.initialControl.setAutoExposureLimit(int(oak_config["ae_max_exposure_us"]))

    color.video.link(uvc.input)

    config = dai.Device.Config()
    config.board.uvc = dai.BoardConfig.UVC(width, height)
    config.board.uvc.frameType = dai.ImgFrame.Type.NV12
    config.board.uvc.cameraName = "OAK RGB"
    pipeline.setBoardConfig(config.board)

    with dai.Device(pipeline) as device:
        info = device.getDeviceInfo()
        print(f"OAK UVC RGB running on {info.name} ({info.mxid})")
        print(
            f"config={args.config}, profile={oak_config['profile']}, sensor={sensor_resolution}, "
            f"uvc={width}x{height}@{fps:g}, fov_scale={fov_scale:g}, isp_scale={_format_isp_scale(isp_scale)}"
        )
        if fov_scale < 1.0:
            print("fov_crop=disabled in OAK UVC; teleimager applies fov_scale after capture")
        if oak_config["manual_exposure_us"] is not None:
            print(
                f"exposure=manual {oak_config['manual_exposure_us']}us "
                f"iso={oak_config['manual_iso']}, anti_banding={oak_config['anti_banding']}"
            )
        else:
            print(
                f"exposure=auto ae_compensation={oak_config['ae_compensation']}, "
                f"ae_max_exposure_us={oak_config['ae_max_exposure_us'] or 'default'}, "
                f"anti_banding={oak_config['anti_banding']}"
            )
        print("Keep this process running while teleimager reads /dev/videoX.")
        while True:
            time.sleep(1)


if __name__ == "__main__":
    main()
