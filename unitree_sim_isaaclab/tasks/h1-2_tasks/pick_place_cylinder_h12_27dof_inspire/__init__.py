
# Copyright (c) 2025, Unitree Robotics Co., Ltd. All Rights Reserved.
# License: Apache License, Version 2.0  

import gymnasium as gym

from . import pickplace_cylinder_h12_27dof_inspire_env_cfg


gym.register(
    id="Isaac-PickPlace-Cylinder-H12-27dof-Inspire-Joint",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    kwargs={
        "env_cfg_entry_point": pickplace_cylinder_h12_27dof_inspire_env_cfg.PickPlaceH1227dofInspireBaseFixEnvCfg,
    },
    disable_env_checker=True,
)
