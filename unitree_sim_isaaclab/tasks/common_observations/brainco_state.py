"""Measured Revo2 state, independent of the task and incoming commands."""
from robots.brainco import joint_names


def get_robot_brainco_joint_states(env):
    from dds.dds_master import dds_manager
    robot = env.scene["robot"]
    names = tuple(robot.data.joint_names)
    cache = getattr(env, "_brainco_state_indices", None)
    if cache is None or cache[0] != names:
        indices = [names.index(n) for side in ("left", "right") for n in joint_names(side)]
        env._brainco_state_indices = (names, indices)
    else:
        indices = cache[1]
    positions = robot.data.joint_pos[:, indices]
    dds = dds_manager.objects.get("brainco")
    if dds is not None:
        dds.write_sim_state(positions[0].detach().cpu().numpy(), robot.data.joint_vel[0, indices].detach().cpu().numpy())
    return positions
