import gymnasium as gym

gym.register(
    id="Isaac-PickPlace-Cylinder-G129-Brainco-Joint",
    entry_point="isaaclab.envs:ManagerBasedRLEnv",
    kwargs={"env_cfg_entry_point": f"{__name__}.env_cfg:PickPlaceG129BraincoJointEnvCfg"},
    disable_env_checker=True,
)
