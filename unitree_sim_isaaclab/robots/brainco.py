"""Official Revo2 model metadata and a hand-only overlay on the existing G1 USD."""

from functools import lru_cache
import hashlib
import math
import os
from pathlib import Path
import xml.etree.ElementTree as ET

MODEL_REVISION = "f332a6f0dc944e26b82976b637074b03f7ee8a2c"
MOUNT_REVISION = "7d6075f7f58588b189b940130e3edab3c839b2df"
SERVICE_REVISION = "d71996b6999edb2f838a3dca3d9621429a2ef966"
JOINT_SUFFIXES = (
    "thumb_proximal_joint", "thumb_metacarpal_joint", "index_proximal_joint",
    "middle_proximal_joint", "ring_proximal_joint", "pinky_proximal_joint",
)
MODEL_DIR = Path("/opt/src/brainco-description/revo2_system")
MOUNT_DIR = Path("/opt/src/unitree_ros/robots/g1_with_brainco_hand")
# Numerical joint-space inertia, not an official hardware/rotor parameter.
# Both sides of each hard mimic constraint need it when the G1 arms accelerate.
SIM_JOINT_ARMATURE = 0.01  # kg m^2; validated for the 5 ms simulation step.


def joint_names(side):
    return [f"{side}_{name}" for name in JOINT_SUFFIXES]


@lru_cache(maxsize=2)
def hand_joints(side):
    root = ET.parse(MODEL_DIR / "urdf" / f"revo2_{side}.urdf").getroot()
    joints = {}
    for joint in root.findall("joint"):
        if joint.get("type") != "revolute":
            continue
        limit = {key: float(value) for key, value in joint.find("limit").attrib.items()}
        mimic = joint.find("mimic")
        limit["mimic"] = None if mimic is None else {
            "joint": mimic.get("joint"), "multiplier": float(mimic.get("multiplier", 1)),
            "offset": float(mimic.get("offset", 0)),
        }
        joints[joint.get("name")] = limit
    if len(joints) != 11 or set(joint_names(side)) != {n for n, j in joints.items() if j["mimic"] is None}:
        raise ValueError(f"Unexpected official Revo2 joint layout: {side}")
    for name, limit in joints.items():
        mimic = limit["mimic"]
        if mimic:
            source = joints[mimic["joint"]]
            endpoints = [source[k] * mimic["multiplier"] + mimic["offset"] for k in ("lower", "upper")]
            if min(endpoints) < limit["lower"] - 1e-6 or max(endpoints) > limit["upper"] + 1e-6:
                raise ValueError(f"Official mimic/limit mismatch: {name}")
    return joints


def drive_velocity_limits(side):
    """Enforce both source and follower URDF speed limits on the driven axis."""
    joints = hand_joints(side)
    limits = {name: joints[name]["velocity"] for name in joint_names(side)}
    for joint in joints.values():
        mimic = joint["mimic"]
        if mimic and mimic["multiplier"]:
            source = mimic["joint"]
            limits[source] = min(limits[source], joint["velocity"] / abs(mimic["multiplier"]))
    return limits


def prepare_usd():
    """Compose references; never edit the original G1 or BrainCo assets."""
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, PhysxSchema

    base = Path(os.environ["PROJECT_ROOT"]) / "assets/robots/g1-29dof-dex3-base-fix-usd/g1_29dof_with_dex3_base_fix.usd"
    mount_urdf = MOUNT_DIR / "g1_29dof_mode_15_brainco_hand.urdf"
    sources = [Path(__file__), mount_urdf, base]
    for side in ("left", "right"):
        sources += [MODEL_DIR / "urdf" / f"revo2_{side}.urdf", MODEL_DIR / "usd" / f"revo2_{side}.usd"]
        sources.append(MOUNT_DIR / "meshes" / f"{side}_base2_link.STL")
    digest = hashlib.sha256()
    for path in sources:
        digest.update(str(path).encode())
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    cache = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "unitree_sim_isaaclab/brainco" / digest.hexdigest()[:20]
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / "g1_brainco.usda"
    if target.exists():
        return str(target)

    # A separate filename allows an interrupted generation to be retried safely.
    temporary = cache / f"g1_brainco_{os.getpid()}.usda"
    stage = Usd.Stage.CreateNew(str(temporary))
    root = UsdGeom.Xform.Define(stage, "/Robot").GetPrim()
    root.GetReferences().AddReference(str(base))
    stage.SetDefaultPrim(root)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)

    def find(name, under=root):
        direct = under.GetChild(name)
        if direct:
            return direct
        matches = [p for p in Usd.PrimRange(under) if p.GetName() == name]
        physics = [p for p in matches if p.IsA(UsdPhysics.Joint) or p.HasAPI(UsdPhysics.RigidBodyAPI)]
        matches = physics or matches
        if len(matches) != 1:
            raise ValueError(f"Expected one prim named {name}, got {len(matches)}")
        return matches[0]

    def pose(origin):
        xyz = [float(x) for x in origin.get("xyz", "0 0 0").split()]
        r, p, y = [float(x) for x in origin.get("rpy", "0 0 0").split()]
        cr, sr, cp, sp, cy, sy = math.cos(r/2), math.sin(r/2), math.cos(p/2), math.sin(p/2), math.cos(y/2), math.sin(y/2)
        q = Gf.Quatd(cr*cp*cy + sr*sp*sy, sr*cp*cy-cr*sp*sy, cr*sp*cy+sr*cp*sy, cr*cp*sy-sr*sp*cy)
        return Gf.Vec3d(*xyz), q

    # USD links are siblings: remove by the joint graph, not namespace ancestry.
    for side in ("left", "right"):
        removed = {find(f"{side}_hand_palm_link").GetPath()}
        joints = [UsdPhysics.Joint(p) for p in Usd.PrimRange(root) if p.IsA(UsdPhysics.Joint)]
        changed = True
        while changed:
            changed = False
            for joint in joints:
                if set(joint.GetBody0Rel().GetTargets()) & removed:
                    new = set(joint.GetBody1Rel().GetTargets()) - removed
                    if new:
                        removed.update(new)
                        changed = True
        for joint in joints:
            if (set(joint.GetBody0Rel().GetTargets()) | set(joint.GetBody1Rel().GetTargets())) & removed:
                joint.GetPrim().SetActive(False)
        for path in removed:
            stage.GetPrimAtPath(path).SetActive(False)

    mount = ET.parse(mount_urdf).getroot()
    for side in ("left", "right"):
        wrist = find(f"{side}_wrist_yaw_link")
        attachment = mount.find(f"joint[@name='{side}_base_joint']")
        if attachment.find("parent").get("link") != wrist.GetName():
            raise ValueError("Unexpected official wrist attachment")
        xyz, quat = pose(attachment.find("origin"))
        hand = UsdGeom.Xform.Define(stage, f"/Robot/{side}_revo2")
        hand.GetPrim().GetReferences().AddReference(str(MODEL_DIR / "usd" / f"revo2_{side}.usd"))
        # Match the initial link poses as well as the fixed-joint frames.
        transform = Gf.Matrix4d().SetRotate(quat)
        transform.SetTranslateOnly(xyz)
        transform = transform * UsdGeom.XformCache().GetLocalToWorldTransform(wrist)
        hand.MakeMatrixXform().Set(transform)
        for prim in list(Usd.PrimRange(hand.GetPrim())):
            if prim.HasAPI(UsdPhysics.ArticulationRootAPI):
                prim.RemoveAPI(UsdPhysics.ArticulationRootAPI)
            if prim.HasAPI(PhysxSchema.PhysxArticulationAPI):
                prim.RemoveAPI(PhysxSchema.PhysxArticulationAPI)
        for name in ("root_joint", f"{side}_hand_base_joint", "world"):
            find(name, hand.GetPrim()).SetActive(False)
        palm = find(f"{side}_hand_base_link", hand.GetPrim())
        fixed = UsdPhysics.FixedJoint.Define(stage, f"/Robot/joints/{side}_brainco_mount")
        fixed.CreateBody0Rel().SetTargets([wrist.GetPath()])
        fixed.CreateBody1Rel().SetTargets([palm.GetPath()])
        fixed.CreateLocalPos0Attr().Set(Gf.Vec3f(xyz))
        fixed.CreateLocalRot0Attr().Set(Gf.Quatf(quat))
        fixed.CreateLocalPos1Attr().Set(Gf.Vec3f(0))
        fixed.CreateLocalRot1Attr().Set(Gf.Quatf(1))

        # Empty URDF tip links are coordinate frames, not massive rigid bodies.
        # PhysX auto-computes a nonzero mass for USD bodies with mass=0. Preserve
        # these frames under their distal links instead of adding fictitious mass.
        urdf = ET.parse(MODEL_DIR / "urdf" / f"revo2_{side}.urdf").getroot()
        connections = {j.find("child").get("link"): j for j in urdf.findall("joint") if j.get("type") == "fixed"}
        for link in urdf.findall("link"):
            name = link.get("name")
            if len(link) or name not in connections:
                continue
            connection = connections[name]
            parent = find(connection.find("parent").get("link"), hand.GetPrim())
            find(name, hand.GetPrim()).SetActive(False)
            find(connection.get("name"), hand.GetPrim()).SetActive(False)
            frame = UsdGeom.Xform.Define(stage, f"{parent.GetPath()}/{name}")
            fx, fq = pose(connection.find("origin"))
            frame.AddTranslateOp().Set(fx)
            frame.AddOrientOp().Set(Gf.Quatf(fq))

        speeds = drive_velocity_limits(side)
        for name, limit in hand_joints(side).items():
            prim = find(name, hand.GetPrim())
            joint = UsdPhysics.RevoluteJoint(prim)
            joint.GetLowerLimitAttr().Set(math.degrees(limit["lower"]))
            joint.GetUpperLimitAttr().Set(math.degrees(limit["upper"]))
            physics = PhysxSchema.PhysxJointAPI.Apply(prim)
            physics.CreateArmatureAttr().Set(SIM_JOINT_ARMATURE)
            physics.CreateMaxJointVelocityAttr().Set(math.degrees(speeds.get(name, limit["velocity"])))
            mimic = limit["mimic"]
            if mimic:
                prim.RemoveAPI(UsdPhysics.DriveAPI, "angular")
                api = PhysxSchema.PhysxMimicJointAPI.Apply(prim, "rotX")
                api.CreateReferenceJointRel().SetTargets([find(mimic["joint"], hand.GetPrim()).GetPath()])
                api.CreateGearingAttr().Set(-mimic["multiplier"])
                api.CreateOffsetAttr().Set(-math.degrees(mimic["offset"]))
            else:
                drive = UsdPhysics.DriveAPI.Apply(prim, "angular")
                drive.CreateMaxForceAttr().Set(limit["effort"])
                # USD angular drives use degrees; IsaacLab uses radians.
                drive.CreateStiffnessAttr().Set(100.0 * math.pi / 180)
                drive.CreateDampingAttr().Set(1.0 * math.pi / 180)

        # The official adapter is a separate fixed body on the wrist.
        adapter_name = f"{side}_base2_link"
        link = mount.find(f"link[@name='{adapter_name}']")
        connection = mount.find(f"joint[@name='{side}_base2_joint']")
        adapter = UsdGeom.Xform.Define(stage, f"/Robot/{adapter_name}")
        ax, aq = pose(connection.find("origin"))
        matrix = Gf.Matrix4d().SetRotate(aq)
        matrix.SetTranslateOnly(ax)
        adapter.MakeMatrixXform().Set(matrix * UsdGeom.XformCache().GetLocalToWorldTransform(wrist))
        UsdPhysics.RigidBodyAPI.Apply(adapter.GetPrim())
        inertial = link.find("inertial")
        mass = UsdPhysics.MassAPI.Apply(adapter.GetPrim())
        mass.CreateMassAttr().Set(float(inertial.find("mass").get("value")))
        center, _ = pose(inertial.find("origin"))
        mass.CreateCenterOfMassAttr().Set(Gf.Vec3f(center))
        # Diagonalize the official inertia tensor (not a guessed inertia).
        import numpy as np
        it = inertial.find("inertia").attrib
        tensor = np.array([[float(it["ixx"]), float(it["ixy"]), float(it["ixz"])], [float(it["ixy"]), float(it["iyy"]), float(it["iyz"])], [float(it["ixz"]), float(it["iyz"]), float(it["izz"])]])
        values, axes = np.linalg.eigh(tensor)
        if np.linalg.det(axes) < 0:
            axes[:, 0] *= -1
        mass.CreateDiagonalInertiaAttr().Set(Gf.Vec3f(*map(float, values)))
        axes_matrix = Gf.Matrix4d(Gf.Matrix3d(*map(float, axes.T.flatten())), Gf.Vec3d(0))
        mass.CreatePrincipalAxesAttr().Set(Gf.Quatf(axes_matrix.ExtractRotationQuat()))
        # STL is converted as geometry only; the robot/hand USDs are not reimported.
        from isaaclab.sim.converters import MeshConverter, MeshConverterCfg
        mesh_path = MOUNT_DIR / link.find("visual/geometry/mesh").get("filename")
        mesh_cfg = MeshConverterCfg(asset_path=str(mesh_path), usd_dir=str(cache / side), usd_file_name="adapter.usd", make_instanceable=False, collision_props=None)
        mesh_usd = MeshConverter(mesh_cfg).usd_path
        mesh = stage.DefinePrim(f"{adapter.GetPath()}/geometry", "Xform")
        mesh.GetReferences().AddReference(mesh_usd)
        for prim in Usd.PrimRange(mesh):
            if prim.IsA(UsdGeom.Mesh):
                UsdPhysics.CollisionAPI.Apply(prim)
                UsdPhysics.MeshCollisionAPI.Apply(prim).CreateApproximationAttr().Set("convexHull")
        adapter_fixed = UsdPhysics.FixedJoint.Define(stage, f"/Robot/joints/{side}_brainco_adapter")
        adapter_fixed.CreateBody0Rel().SetTargets([wrist.GetPath()])
        adapter_fixed.CreateBody1Rel().SetTargets([adapter.GetPath()])
        adapter_fixed.CreateLocalPos0Attr().Set(Gf.Vec3f(ax))
        adapter_fixed.CreateLocalRot0Attr().Set(Gf.Quatf(aq))
    stage.GetRootLayer().Save()
    os.replace(temporary, target)
    return str(target)


def spawn_brainco(prim_path, cfg, translation=None, orientation=None, **kwargs):
    from isaaclab.sim.spawners.from_files import spawn_from_usd
    return spawn_from_usd(prim_path, cfg.replace(usd_path=prepare_usd()), translation, orientation, **kwargs)


def robot_config():
    from isaaclab.actuators import ImplicitActuatorCfg
    from robots.unitree import G129_CFG_WITH_DEX3_BASE_FIX
    cfg = G129_CFG_WITH_DEX3_BASE_FIX.copy()
    cfg.spawn.func = spawn_brainco
    cfg.actuators.pop("hands")
    cfg.actuators["brainco"] = ImplicitActuatorCfg(
        joint_names_expr=joint_names("left") + joint_names("right"),
        stiffness=100.0, damping=1.0, effort_limit_sim=None, velocity_limit_sim=None,
        armature=None,  # Read the same authored value as the passive mimic joints.
    )
    # Passive mimic joints deliberately have no actuator and no angular drive.
    cfg.init_state.joint_pos = {n: v for n, v in cfg.init_state.joint_pos.items() if "_hand_" not in n}
    cfg.init_state.joint_pos[".*_(metacarpal|proximal|distal)_joint"] = 0.0
    return cfg
