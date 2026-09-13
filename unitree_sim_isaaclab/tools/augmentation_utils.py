# utils/augmentation_utils.py

import random
from pxr import UsdShade, UsdLux, UsdGeom, Gf, Sdf
import omni.usd

# ------------------------------
# 通用安全设置属性函数，避免重复创建属性
def safe_set_attr(prim, attr_name, value, usd_type):
    attr = prim.GetAttribute(attr_name)
    if not attr.IsValid():
        attr = prim.CreateAttribute(attr_name, usd_type)
    attr.Set(value)

# ------------------------------
# 修改光源属性（颜色、强度、旋转、位置等）
def update_light(
    prim_path: str,
    color=(1.0, 1.0, 1.0),
    intensity=5000.0,
    rotation=(0.0, 0.0, 0.0),
    position=None,
    radius=None,
    enabled=None,
    temperature=None,
    cast_shadows=None,
):
    """
    更新光源属性，支持不同光源类型。
    支持参数包括颜色、强度、旋转角度、位置、半径、是否开启、色温、阴影开启等。

    Args:
        prim_path: USD Prim 路径，如 "/World/light"
        color: 光颜色 RGB tuple，范围0-1
        intensity: 光强度
        rotation: 旋转角 (度)，tuple(x,y,z)
        position: 位置坐标 tuple(x,y,z) 或 None（不改位置）
        radius: 仅 SphereLight 支持，半径
        enabled: 是否启用光源，bool 或 None
        temperature: 色温，仅部分光源支持
        cast_shadows: 是否投射阴影，bool 或 None
    """
    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPrimAtPath(prim_path)
    if not prim.IsValid():
        raise RuntimeError(f"[update_light] ❌ 找不到光源 Prim: {prim_path}")

    type_name = prim.GetTypeName()
    print(f"[update_light] ✅ 光源类型: {type_name}")

    # 设置位姿属性（旋转和平移）
    safe_set_attr(prim, "xformOp:rotateXYZ", Gf.Vec3f(*rotation), Sdf.ValueTypeNames.Float3)
    if position is not None:
        safe_set_attr(prim, "xformOp:translate", Gf.Vec3f(*position), Sdf.ValueTypeNames.Float3)

    # 识别光源类型并创建对应接口
    light = None
    if type_name == "DomeLight":
        light = UsdLux.DomeLight(prim)
    elif type_name == "DistantLight":
        light = UsdLux.DistantLight(prim)
    elif type_name == "SphereLight":
        light = UsdLux.SphereLight(prim)
    elif type_name == "RectLight":
        light = UsdLux.RectLight(prim)
    else:
        # 未知光源类型使用通用接口
        print(f"[update_light] ⚠️ 未知光源类型 {type_name}，使用通用接口设置 color 和 intensity")
        safe_set_attr(prim, "color", Gf.Vec3f(*color), Sdf.ValueTypeNames.Color3f)
        safe_set_attr(prim, "intensity", intensity, Sdf.ValueTypeNames.Float)
        return

    # 通用属性设置
    light.CreateColorAttr().Set(Gf.Vec3f(*color))
    light.CreateIntensityAttr().Set(intensity)

    # 有条件地设置其他属性
    if enabled is not None and type_name in ["SphereLight", "DistantLight", "RectLight"]:
        light.CreateEnableAttr().Set(enabled)

    if cast_shadows is not None and type_name in ["SphereLight", "DistantLight", "RectLight"]:
        light.CreateShadowEnableAttr().Set(cast_shadows)

    if temperature is not None and hasattr(light, "CreateTemperatureAttr"):
        light.CreateTemperatureAttr().Set(temperature)

    if radius is not None and type_name == "SphereLight":
        light.CreateRadiusAttr().Set(radius)

    print(f"[update_light] ✅ 光源 {prim_path} 设置完成")


# ------------------------------
# 修改相机属性，支持焦距、传感器尺寸、曝光、焦点距离等
def augment_camera_appearance(
    camera_path: str,
    focal_length: float = None,
    horizontal_aperture: float = None,
    vertical_aperture: float = None,
    exposure: float = None,
    focus_distance: float = None,
):
    """
    修改静态相机的视觉成像属性，用于增强数据多样性。
    支持调整焦距、视野范围、曝光、景深等。

    Args:
        camera_path: USD 相机 Prim 路径
        focal_length: 焦距（单位 mm）
        horizontal_aperture: 传感器宽度（单位 mm）
        vertical_aperture: 传感器高度（单位 mm）
        exposure: 曝光值
        focus_distance: 聚焦距离（景深效果）
    """
    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPrimAtPath(camera_path)

    if not prim or not prim.IsValid():
        raise RuntimeError(f"[augment_camera_appearance] ❌ 找不到相机 prim: {camera_path}")

    camera = UsdGeom.Camera(prim)

    if focal_length is not None:
        camera.CreateFocalLengthAttr().Set(focal_length)

    if horizontal_aperture is not None:
        camera.CreateHorizontalApertureAttr().Set(horizontal_aperture)

    if vertical_aperture is not None:
        camera.CreateVerticalApertureAttr().Set(vertical_aperture)

    if exposure is not None:
        camera.CreateExposureAttr().Set(exposure)

    if focus_distance is not None:
        camera.CreateFocusDistanceAttr().Set(focus_distance)

    print(f"[augment_camera_appearance] ✅ 设置相机 {camera_path} 属性完成")

# --- 新增：批量修改相机（根据名称关键词匹配） ---
def batch_augment_cameras_by_name(
    names,
    focal_length=None,
    horizontal_aperture=None,
    vertical_aperture=None,
    exposure=None,
    focus_distance=None,
):
    """
    批量修改场景中所有名称包含 names 中任意关键词的相机属性。

    参数:
        names: list[str] — 相机名称关键词，如 ["front_cam", "wrist_camera"]
        其余参数: 可为单值（广播）或与匹配的相机数量一致的列表（逐个赋值）
    """
    from pxr import UsdGeom
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        raise RuntimeError("[batch_augment_cameras_by_name] USD Stage 未初始化")

    matched_prims = []

    def traverse_prim(prim):
        if not prim or not prim.IsValid():
            return
        if prim.IsA(UsdGeom.Camera):
            prim_name = prim.GetName()
            if any(name in prim_name for name in names):
                matched_prims.append(prim)
        for child in prim.GetChildren():
            traverse_prim(child)

    traverse_prim(stage.GetPseudoRoot())

    if not matched_prims:
        print("[batch_augment_cameras_by_name] ⚠️ 没有找到匹配的相机")
        return

    # 参数展开工具
    def normalize(param, default=None):
        if isinstance(param, (list, tuple)):
            if len(param) == len(matched_prims):
                return param
        return [param if param is not None else default] * len(matched_prims)

    focal_lengths = normalize(focal_length)
    horiz_apertures = normalize(horizontal_aperture)
    vert_apertures = normalize(vertical_aperture)
    exposures = normalize(exposure)
    focus_distances = normalize(focus_distance)

    for i, prim in enumerate(matched_prims):
        try:
            augment_camera_appearance(
                camera_path=prim.GetPath().pathString,
                focal_length=focal_lengths[i],
                horizontal_aperture=horiz_apertures[i],
                vertical_aperture=vert_apertures[i],
                exposure=exposures[i],
                focus_distance=focus_distances[i],
            )
        except Exception as e:
            print(f"[batch_augment_cameras_by_name] 修改相机 {prim.GetPath().pathString} 出错: {e}")

    print(f"[batch_augment_cameras_by_name] ✅ 批量修改完成，目标数: {len(matched_prims)}")





