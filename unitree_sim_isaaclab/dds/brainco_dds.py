"""Reproduce the position interface of Unitree brainco_hand_service d71996b6.

Speed is approximated using URDF limits. tau_est (hardware current) is unsupported.
"""
import logging
import numpy as np
from dds.dds_base import DDSObject
from dds.sharedmemorymanager import SharedMemoryManager
from robots.brainco import hand_joints, joint_names
from unitree_sdk2py.core.channel import ChannelPublisher, ChannelSubscriber
from unitree_sdk2py.idl.unitree_go.msg.dds_ import MotorCmds_, MotorStates_
from unitree_sdk2py.idl.default import unitree_go_msg_dds__MotorState_


def command_values(msg):
    if len(msg.cmds) != 6:
        raise ValueError("BrainCo commands must have exactly 6 motors")
    # DDS q/dq are float32; preserve the C++ clamp -> multiply -> uint16 conversion.
    values = np.asarray([[m.q, m.dq] for m in msg.cmds], dtype=np.float32)
    if not np.isfinite(values).all():
        raise ValueError("BrainCo q/dq must be finite")
    return (np.clip(values, 0, 1) * np.float32(1000)).astype(np.uint16).astype(float) / 1000


class BraincoDDS(DDSObject):
    def __init__(self):
        super().__init__()
        self.node_name = "brainco"
        self.input_shm = SharedMemoryManager(size=4096)
        self.commands = {side: SharedMemoryManager(size=1024) for side in ("left", "right")}
        self.limits = {}
        for side, shm in self.commands.items():
            shm.write_data({"q": [0.0] * 6, "dq": [1.0] * 6})
            joints = hand_joints(side)
            self.limits[side] = np.asarray([[joints[n][k] for k in ("lower", "upper", "velocity")] for n in joint_names(side)])
        self.publishers = {}
        self.subscribers = {}

    def setup_publisher(self):
        for side in self.commands:
            publisher = ChannelPublisher(f"rt/brainco/{side}/state", MotorStates_)
            publisher.Init()
            self.publishers[side] = publisher
        return True

    def setup_subscriber(self):
        for side in self.commands:
            subscriber = ChannelSubscriber(f"rt/brainco/{side}/cmd", MotorCmds_)
            subscriber.Init(lambda msg, side=side: self.dds_subscriber(msg, side), 32)
            self.subscribers[side] = subscriber
        return True

    def dds_subscriber(self, msg, datatype):
        try:
            values = command_values(msg)
        except ValueError as error:
            logging.getLogger(__name__).warning("Ignoring invalid %s command: %s", datatype, error)
            return
        self.commands[datatype].write_data({"q": values[:, 0].tolist(), "dq": values[:, 1].tolist()})

    def get_hand_commands(self):
        return {side: shm.read_data() for side, shm in self.commands.items()}

    def write_sim_state(self, positions, velocities):
        # Arguments are measured positions/velocities, left then right, in DDS order.
        if not np.isfinite(positions).all() or not np.isfinite(velocities).all():
            return
        self.input_shm.write_data({"positions": np.asarray(positions).tolist(), "velocities": np.asarray(velocities).tolist()})

    def dds_publisher(self):
        data = self.input_shm.read_data()
        if data is None:
            return
        for i, side in enumerate(self.commands):
            limits = self.limits[side]
            pos = np.asarray(data["positions"][i*6:(i+1)*6])
            vel = np.asarray(data["velocities"][i*6:(i+1)*6])
            q = np.round(np.clip((pos - limits[:, 0]) / (limits[:, 1] - limits[:, 0]), 0, 1) * 1000) / 1000
            dq = np.round(np.clip(vel / limits[:, 2], -1, 1) * 1000) / 1000
            message = MotorStates_()
            message.states = [unitree_go_msg_dds__MotorState_() for _ in range(6)]
            for j, motor in enumerate(message.states):
                motor.q, motor.dq, motor.tau_est = float(q[j]), float(dq[j]), 0.0
            self.publishers[side].Write(message)

    def stop_communication(self):
        super().stop_communication()
        for channel in [*self.subscribers.values(), *self.publishers.values()]:
            channel.Close()
        self.subscribers.clear()
        self.publishers.clear()
        self.input_shm.cleanup()
        for shm in self.commands.values():
            shm.cleanup()
