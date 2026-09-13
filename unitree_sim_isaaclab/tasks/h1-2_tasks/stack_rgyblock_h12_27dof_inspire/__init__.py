# Copyright (c) 2025, Unitree Robotics Co., Ltd. All Rights Reserved.
# License: Apache License, Version 2.0  
import gymnasium as gym
import os

from . import stack_rgyblock_h12_27dof_inspire_joint_env_cfg


gym.register(
    id="Isaac-Stack-RgyBlock-H12-27dof-Inspire-Joint",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    kwargs={
        "env_cfg_entry_point": stack_rgyblock_h12_27dof_inspire_joint_env_cfg.StackRgyBlockH1227dofInspireBaseFixEnvCfg,
    },
    disable_env_checker=True,
)

