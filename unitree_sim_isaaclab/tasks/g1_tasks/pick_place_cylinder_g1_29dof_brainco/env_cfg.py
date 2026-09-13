"""Reuse the Dex3 cylinder scene, cameras, reset, rewards and timing."""
from isaaclab.managers import ObservationTermCfg as ObsTerm
from isaaclab.utils import configclass
from tasks.common_config import G1RobotPresets
from tasks.common_observations.brainco_state import get_robot_brainco_joint_states
from tasks.g1_tasks.pick_place_cylinder_g1_29dof_dex3.pickplace_cylinder_g1_29dof_dex3_joint_env_cfg import (
    ObjectTableSceneCfg, ObservationsCfg, PickPlaceG129DEX3JointEnvCfg,
)


@configclass
class BraincoSceneCfg(ObjectTableSceneCfg):
    robot = G1RobotPresets.g1_29dof_brainco_base_fix()


@configclass
class BraincoObservationsCfg(ObservationsCfg):
    @configclass
    class PolicyCfg(ObservationsCfg.PolicyCfg):
        robot_gipper_state = ObsTerm(func=get_robot_brainco_joint_states)
    policy = PolicyCfg()


@configclass
class PickPlaceG129BraincoJointEnvCfg(PickPlaceG129DEX3JointEnvCfg):
    scene = BraincoSceneCfg(num_envs=1, env_spacing=2.5, replicate_physics=True)
    observations = BraincoObservationsCfg()
