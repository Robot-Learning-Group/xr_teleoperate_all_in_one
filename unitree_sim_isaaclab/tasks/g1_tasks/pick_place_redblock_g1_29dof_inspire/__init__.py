# Copyright (c) 2025, Unitree Robotics Co., Ltd. All Rights Reserved.
# License: Apache License, Version 2.0  
import gymnasium as gym
import os

from . import pickplace_redblock_g1_29dof_inspire_joint_env_cfg


gym.register(
    id="Isaac-PickPlace-RedBlock-G129-Inspire-Joint",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    kwargs={
        "env_cfg_entry_point": pickplace_redblock_g1_29dof_inspire_joint_env_cfg.PickPlaceG129InspireHandBaseFixEnvCfg,
    },
    disable_env_checker=True,
)

