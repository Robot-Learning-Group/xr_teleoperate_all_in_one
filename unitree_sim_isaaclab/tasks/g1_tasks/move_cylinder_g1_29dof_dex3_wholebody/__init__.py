
# Copyright (c) 2025, Unitree Robotics Co., Ltd. All Rights Reserved.
# License: Apache License, Version 2.0  

import gymnasium as gym

from . import move_cylinder_g1_29dof_dex3_hw_env_cfg


gym.register(
    id="Isaac-Move-Cylinder-G129-Dex3-Wholebody",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    kwargs={
        "env_cfg_entry_point": move_cylinder_g1_29dof_dex3_hw_env_cfg.MoveCylinderG129Dex3WholebodyEnvCfg,
    },
    disable_env_checker=True,
)

