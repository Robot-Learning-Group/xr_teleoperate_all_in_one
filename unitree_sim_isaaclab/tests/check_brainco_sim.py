"""Physics regression in an isolated Docker network, using unitree_sim_env.

Run: python tests/check_brainco_sim.py [--images /tmp/brainco-frames]
Exercises the shared-memory command path. test_brainco.py tests DDS transport.
Quest operation, grasp success, and XR recording are separate manual checks.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import traceback

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
os.environ.setdefault("PROJECT_ROOT", str(SOURCE))


def run(images):
    import numpy as np
    import torch
    from types import SimpleNamespace
    from isaaclab.envs import ManagerBasedRLEnv
    from isaaclab.sensors import CameraCfg
    from unitree_sdk2py.core.channel import ChannelFactoryInitialize
    from unitree_sdk2py.idl.default import unitree_hg_msg_dds__LowCmd_, unitree_go_msg_dds__MotorCmd_
    from unitree_sdk2py.idl.unitree_go.msg.dds_ import MotorCmds_

    ChannelFactoryInitialize(1, "lo")
    from tasks.g1_tasks.pick_place_cylinder_g1_29dof_brainco.env_cfg import PickPlaceG129BraincoJointEnvCfg
    from action_provider.action_provider_dds import DDSActionProvider
    from dds.dds_create import create_dds_objects
    from robots.brainco import hand_joints, joint_names

    cfg = PickPlaceG129BraincoJointEnvCfg()
    cfg.sim.device = "cpu"  # Match docker/entrypoint.sh.
    cfg.seed = 42
    if images is None:
        for name, value in vars(cfg.scene).items():
            if isinstance(value, CameraCfg):
                setattr(cfg.scene, name, None)
        cfg.observations.policy.camera_image = None
    else:
        images.mkdir(parents=True, exist_ok=True)
    env = ManagerBasedRLEnv(cfg)
    manager = None
    try:
        env.reset()
        args = SimpleNamespace(robot_type="g129", enable_dex1_dds=False,
                               enable_dex3_dds=False, enable_inspire_dds=False,
                               enable_brainco_dds=True, enable_wholebody_dds=False,
                               task="Isaac-PickPlace-Cylinder-G129-Brainco-Joint")
        _, _, manager = create_dds_objects(args, env)
        provider = DDSActionProvider(env, args)
        body, hand = manager.get_object("g129"), manager.get_object("brainco")
        robot = env.scene["robot"]
        names = robot.data.joint_names
        joints = {name: limit for side in ("left", "right") for name, limit in hand_joints(side).items()}
        hand_ids = [names.index(name) for name in joints]
        state_ids = [names.index(name) for side in ("left", "right") for name in joint_names(side)]
        arm_ids = [i for i, name in enumerate(names) if any(part in name for part in ("shoulder", "elbow", "wrist", "waist"))]
        leg_ids = [i for i in range(len(names)) if i not in hand_ids + arm_ids]
        limits = robot.data.joint_pos_limits[0]
        speeds = torch.tensor([limit["velocity"] for limit in joints.values()])
        cmd = unitree_hg_msg_dds__LowCmd_()
        assert hand.input_shm.read_data() is not None, "Missing state before the first command"
        metrics = dict(mimic_error=0., hand_limit_error=0., hand_velocity=0.,
                       state_error=0., state_target_difference=0., leg_limit_error=0.)

        def hand_command(side, values):
            msg = MotorCmds_()
            msg.cmds = [unitree_go_msg_dds__MotorCmd_() for _ in range(6)]
            for motor, value in zip(msg.cmds, values):
                motor.q, motor.dq = float(value), 1.
            hand.dds_subscriber(msg, side)

        with torch.inference_mode():
            for step in range(2400):
                # Include abrupt tracking starts, then continuously moving wrists.
                if step in (100, 1000, 1300) or step >= 1600:
                    pose = [-.4, .2, 0., 1., 0., 0., 0., -.4, -.2, 0., 1., 0., 0., 0.]
                    if step == 1000:
                        pose = [0.] * 14
                    elif step == 1300:
                        pose = [-.3, .3, .1, .8, .4, .2, -.3, -.3, -.3, -.1, .8, -.4, -.2, .3]
                    elif step >= 1600:
                        s = np.sin((step - 1600) * env.step_dt)
                        pose = [-.4, .25, .1*s, .8+.2*s, .4*s, .25*s, .3*s,
                                -.4, -.25, -.1*s, .8+.2*s, -.4*s, -.25*s, -.3*s]
                    for motor, value in zip(cmd.motor_cmd[15:29], pose):
                        motor.q = float(value)
                    cmd.crc = body.crc.Crc(cmd)
                    body.dds_subscriber(cmd, "")
                    assert body.get_robot_command()["motor_cmd"]["positions"][15:29] == [m.q for m in cmd.motor_cmd[15:29]], "Arm command rejected"
                if step in (100, 400, 700, 1000, 1300):
                    value = {100: .5, 400: 1., 700: 0., 1000: 1., 1300: .5}[step]
                    for side in ("left", "right"):
                        hand_command(side, [value] * 6)
                elif step >= 1600:
                    phase = (step - 1600) * env.step_dt + np.arange(6) * .5
                    hand_command("left", (1 + np.sin(phase)) / 2)
                    hand_command("right", (1 - np.sin(phase)) / 2)
                env.step(provider.get_action(env))
                q, v = robot.data.joint_pos[0], robot.data.joint_vel[0]
                assert torch.isfinite(q).all() and torch.isfinite(v).all(), (step, "non-finite robot state")
                assert q.abs().max() < 10., (step, "robot diverged")
                violation = torch.maximum(limits[:, 0] - q, q - limits[:, 1]).clamp_min(0)
                assert violation[hand_ids].max() < .01, (step, "hand position limit", float(violation[hand_ids].max()))
                assert violation[arm_ids].max() < .03, (step, "arm position limit")
                assert (v[hand_ids].abs() <= speeds + .05).all(), (step, "hand velocity limit")
                metrics["hand_limit_error"] = max(metrics["hand_limit_error"], float(violation[hand_ids].max()))
                metrics["hand_velocity"] = max(metrics["hand_velocity"], float(v[hand_ids].abs().max()))
                # Report the existing body's leg issue separately; never label this
                # hand regression as proof that the entire robot is stable.
                metrics["leg_limit_error"] = max(metrics["leg_limit_error"], float(violation[leg_ids].max()))
                for name, limit in joints.items():
                    mimic = limit["mimic"]
                    if mimic:
                        error = abs(float(q[names.index(name)] - mimic["multiplier"] * q[names.index(mimic["joint"])]) - mimic["offset"])
                        assert error < .01, (step, name, "mimic error", error)
                        metrics["mimic_error"] = max(metrics["mimic_error"], error)
                measured = np.asarray(hand.input_shm.read_data()["positions"])
                error = float(np.abs(measured - q[state_ids].cpu().numpy()).max())
                assert error < 1e-6, (step, "state is not measured joint position", error)
                metrics["state_error"] = max(metrics["state_error"], error)
                for side in ("left", "right"):
                    ids = [names.index(name) for name in joint_names(side)]
                    error = float((q[ids] - provider._brainco_targets[side]).abs().max())
                    metrics["state_target_difference"] = max(metrics["state_target_difference"], error)
                if step % 400 == 0:
                    print(f"Physics step {step}/2400", flush=True)
                if images is not None and step in (0, 110, 699, 1599, 2399):
                    from PIL import Image
                    for camera in ("world_camera", "front_camera", "left_wrist_camera", "right_wrist_camera"):
                        pixels = env.scene[camera].data.output["rgb"][0].cpu().numpy()
                        Image.fromarray(pixels).save(images / f"{camera}_{step}.png")
                if step == 1500:
                    env.reset()
        assert metrics["state_target_difference"] > .01, "Measured-state/target distinction was not exercised"
        print("HAND_REGRESSION_PASSED", json.dumps(metrics), flush=True)
        if metrics["leg_limit_error"] > .03:
            print("UNRESOLVED: the unchanged G1 legs exceed joint limits; this is not a whole-robot stability pass.", flush=True)
    finally:
        if manager is not None:
            manager.stop_all_communication()
        env.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path)
    args = parser.parse_args()
    from isaaclab.app import AppLauncher
    app = AppLauncher(headless=True, enable_cameras=args.images is not None).app
    result = 1
    try:
        run(args.images)
        result = 0
    except Exception:
        traceback.print_exc()
    finally:
        # Kit/DDS background threads can keep shutdown alive. Only a completed
        # test reaches result=0; assertions and exceptions retain a failing exit.
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(result)
