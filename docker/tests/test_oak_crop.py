"""Hardware-free crop regression test; pass the patched image_server.py path."""
import ast
import sys
from pathlib import Path

import cv2
import numpy as np
import yaml

source = Path(sys.argv[1])
tree = ast.parse(source.read_text())
node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "OpenCVCamera")
namespace = {"BaseCamera": object, "cv2": cv2}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"), namespace)
camera = object.__new__(namespace["OpenCVCamera"])
camera._img_shape = [480, 640]
camera._crop_scale = 0.70
frame = np.arange(1520 * 2028 * 3, dtype=np.uint8).reshape(1520, 2028, 3)
width, height = camera._crop_size(2028, 1520)
assert (width, height) == (1419, 1064)
x, y = (2028 - width) // 2, (1520 - height) // 2
expected = cv2.resize(frame[y:y + height, x:x + width], (640, 480), interpolation=cv2.INTER_LINEAR)
np.testing.assert_array_equal(camera._apply_crop_scale(frame), expected)
# Cameras without crop configuration must preserve even unexpected dimensions.
namespace.update({"Path": Path, "yaml": yaml, "CONFIG_DIR": Path(__file__).resolve().parents[1]})
helpers = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ("_load_crop_scale", "_resolve_config_relative_path")]
exec(compile(ast.Module(body=helpers, type_ignores=[]), str(source), "exec"), namespace)
config = yaml.safe_load((namespace["CONFIG_DIR"] / "cam_config_server.yaml").read_text())
assert namespace["_load_crop_scale"](config["head_camera"]) == 0.70
for name in ("left_wrist_camera", "right_wrist_camera"):
    camera._crop_scale = namespace["_load_crop_scale"](config[name])
    assert camera._crop_scale is None
    assert camera._apply_crop_scale(frame) is frame
camera._crop_scale = 1.0
assert camera._apply_crop_scale(frame).shape == (480, 640, 3)
assert camera._apply_crop_scale(None) is None
print("OAK center crop, output dimensions, wrist passthrough: OK")
