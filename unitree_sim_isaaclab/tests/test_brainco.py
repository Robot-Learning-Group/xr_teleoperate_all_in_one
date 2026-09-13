"""Run in unitree_sim_env: python -m unittest discover -s tests -p test_brainco.py."""
import time
import unittest
import numpy as np
from unitree_sdk2py.core.channel import ChannelFactoryInitialize, ChannelPublisher, ChannelSubscriber
from unitree_sdk2py.idl.unitree_go.msg.dds_ import MotorCmds_, MotorStates_
from unitree_sdk2py.idl.default import unitree_go_msg_dds__MotorCmd_
from dds.brainco_dds import BraincoDDS, command_values
from robots.brainco import drive_velocity_limits, hand_joints, joint_names


def command(q, dq=1.0):
    msg = MotorCmds_()
    msg.cmds = [unitree_go_msg_dds__MotorCmd_() for _ in range(6)]
    for motor, value in zip(msg.cmds, q):
        motor.q, motor.dq = float(value), float(dq)
    return msg


class BraincoTests(unittest.TestCase):
    def test_official_motor_order_and_limits(self):
        for side in ("left", "right"):
            joints = hand_joints(side)
            self.assertEqual(joint_names(side)[:2], [f"{side}_thumb_proximal_joint", f"{side}_thumb_metacarpal_joint"])
            self.assertEqual(sum(j["mimic"] is None for j in joints.values()), 6)
            self.assertEqual(sum(j["mimic"] is not None for j in joints.values()), 5)

    def test_mimic_speed_limits_are_enforced_through_source(self):
        for side in ("left", "right"):
            joints = hand_joints(side)
            speeds = drive_velocity_limits(side)
            for name, speed in speeds.items():
                self.assertLessEqual(speed, joints[name]["velocity"])
            for joint in joints.values():
                mimic = joint["mimic"]
                if mimic:
                    self.assertLessEqual(speeds[mimic["joint"]] * abs(mimic["multiplier"]), joint["velocity"] + 1e-12)

    def test_service_float32_clamp_and_truncation(self):
        values = command_values(command([-1, 0, .1239, .5, 1, 2], .4569))
        np.testing.assert_allclose(values[:, 0], [0, 0, .123, .5, 1, 1])
        np.testing.assert_allclose(values[:, 1], [.456] * 6)
        for invalid in (float("nan"), float("inf"), -float("inf")):
            with self.assertRaises(ValueError):
                command_values(command([invalid] * 6))
            with self.assertRaises(ValueError):
                command_values(command([0] * 6, invalid))
        for size in (0, 5, 7):
            msg = command([0] * 6)
            msg.cmds = [unitree_go_msg_dds__MotorCmd_() for _ in range(size)]
            with self.assertRaises(ValueError):
                command_values(msg)

    def test_real_dds_initial_state_commands_and_measured_feedback(self):
        # Isolated Docker network: same simulation domain without touching a running sim.
        ChannelFactoryInitialize(1, "lo")
        dds = BraincoDDS()
        clients = []
        try:
            dds.setup_publisher()
            dds.setup_subscriber()
            received = {side: [] for side in ("left", "right")}
            senders = {}
            for side in received:
                receiver = ChannelSubscriber(f"rt/brainco/{side}/state", MotorStates_)
                receiver.Init(lambda msg, side=side: received[side].append(msg), 32)
                sender = ChannelPublisher(f"rt/brainco/{side}/cmd", MotorCmds_)
                sender.Init()
                senders[side] = sender
                clients += [receiver, sender]
            q = np.concatenate([dds.limits[s][:, 0] + .25 * (dds.limits[s][:, 1] - dds.limits[s][:, 0]) for s in received])
            v = np.concatenate([-.5 * dds.limits[s][:, 2] for s in received])
            dds.write_sim_state(q, v)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not all(received.values()):
                dds.dds_publisher()
                time.sleep(.01)
            self.assertTrue(all(received.values()), "No state before the first command")
            for side in received:
                np.testing.assert_allclose([m.q for m in received[side][-1].states], [.25] * 6)
                np.testing.assert_allclose([m.dq for m in received[side][-1].states], [-.5] * 6)
                self.assertTrue(all(m.tau_est == 0 for m in received[side][-1].states))
            for side in received:
                for axis in range(6):
                    for value in (0, .5, 1):
                        positions = [0] * 6
                        positions[axis] = value
                        deadline = time.monotonic() + 2
                        while time.monotonic() < deadline:
                            senders[side].Write(command(positions))
                            time.sleep(.01)
                            if dds.get_hand_commands()[side]["q"] == positions:
                                break
                        self.assertEqual(dds.get_hand_commands()[side]["q"], positions)
            before = dds.get_hand_commands()["right"]["q"]
            senders["left"].Write(command([.75] * 6))
            time.sleep(.05)
            self.assertEqual(dds.get_hand_commands()["right"]["q"], before)
            senders["left"].Write(command([float("nan")] * 6))
            time.sleep(.05)
            self.assertEqual(dds.get_hand_commands()["left"]["q"], [.75] * 6)
            dds.dds_publisher()
            time.sleep(.05)
            np.testing.assert_allclose([m.q for m in received["left"][-1].states], [.25] * 6)
        finally:
            for client in clients:
                client.Close()
            dds.stop_communication()


if __name__ == "__main__":
    unittest.main()
