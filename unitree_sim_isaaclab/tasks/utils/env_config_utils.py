"""
环境配置工具模块
提供增强的环境配置管理和参数传递功能
"""

import argparse
from typing import Dict, Any, Optional
from pathlib import Path


def create_enhanced_env_cfg(task_name: str, args: argparse.Namespace):
    """创建增强的环境配置
    
    Args:
        task_name: 任务名称
        args: 命令行参数
        
    Returns:
        环境配置对象
    """
    
    # 根据任务名称选择合适的配置创建方法
    if "Isaac-PickPlace-G129" in task_name:
        return create_g129_pickplace_cfg(args)
    else:
        # 回退到标准方法
        from isaaclab_tasks.utils.parse_cfg import parse_env_cfg
        return parse_env_cfg(task_name, device=args.device, num_envs=getattr(args, 'num_envs', 1))


def create_g129_pickplace_cfg(args: argparse.Namespace):
    """创建G129抓取放置任务的环境配置
    
    Args:
        args: 命令行参数
        
    Returns:
        PickPlaceG129DEX1JointWaistFixEnvCfg: 环境配置
    """
    from tasks.g1_tasks.pick_place_cylinder_g1_29dof_dex1.pickplace_cylinder_g1_29dof_dex1_joint_env_cfg import (
        PickPlaceG129DEX1JointWaistFixEnvCfg
    )
    
    # 从args中提取参数
    num_envs = getattr(args, 'num_envs', 1)
    device = getattr(args, 'device', 'cuda')
    env_spacing = getattr(args, 'env_spacing', 2.5)
    
    # 使用新的创建方法
    env_cfg = PickPlaceG129DEX1JointWaistFixEnvCfg.create_with_params(
        num_envs=num_envs,
        device=device,
        env_spacing=env_spacing
    )
    
    # 设置任务名称
    env_cfg.env_name = args.task
    
    # 应用其他配置
    apply_performance_optimizations(env_cfg, args)
    apply_termination_settings(env_cfg, args)
    
    return env_cfg


def apply_performance_optimizations(env_cfg, args: argparse.Namespace):
    """应用性能优化设置
    
    Args:
        env_cfg: 环境配置
        args: 命令行参数
    """
    
    # 根据精度模式调整仿真参数
    precision_mode = getattr(args, 'precision_mode', 'balanced')
    
    if precision_mode == 'fast':
        # 快速模式：降低精度，提高速度
        env_cfg.sim.dt = 0.01  # 更大的时间步长
        if hasattr(env_cfg.sim, 'substeps'):
            env_cfg.sim.substeps = 1
            
    elif precision_mode == 'precise':
        # 精确模式：提高精度，可能降低速度
        env_cfg.sim.dt = 0.002  # 更小的时间步长
        if hasattr(env_cfg.sim, 'substeps'):
            env_cfg.sim.substeps = 4
            
    else:  # balanced
        # 平衡模式：默认设置
        env_cfg.sim.dt = 0.005
        if hasattr(env_cfg.sim, 'substeps'):
            env_cfg.sim.substeps = 2
    
    # 根据优化设置调整渲染频率
    if getattr(args, 'disable_optimizations', False):
        # 禁用优化时使用标准设置
        pass
    else:
        # 启用优化时调整设置
        if hasattr(env_cfg, 'decimation'):
            # 根据step_hz调整decimation
            step_hz = getattr(args, 'step_hz', 500)
            if step_hz > 300:
                env_cfg.decimation = 2  # 更高的控制频率
            elif step_hz < 100:
                env_cfg.decimation = 8  # 更低的控制频率


def apply_termination_settings(env_cfg, args: argparse.Namespace):
    """应用终止条件设置
    
    Args:
        env_cfg: 环境配置
        args: 命令行参数
    """
    
    # 根据参数决定是否移除超时终止条件
    if getattr(args, 'disable_timeout', True):  # 默认禁用超时
        if hasattr(env_cfg.terminations, 'time_out'):
            env_cfg.terminations.time_out = None
    
    # 设置episode长度
    episode_length = getattr(args, 'episode_length', 20.0)
    env_cfg.episode_length_s = episode_length


def add_env_config_args(parser: argparse.ArgumentParser):
    """添加环境配置相关的命令行参数
    
    Args:
        parser: 参数解析器
    """
    
    # 环境基本参数
    env_group = parser.add_argument_group('环境配置参数')
    env_group.add_argument("--num_envs", type=int, default=1, help="环境数量")
    env_group.add_argument("--env_spacing", type=float, default=2.5, help="环境间距")
    env_group.add_argument("--episode_length", type=float, default=20.0, help="Episode长度（秒）")
    env_group.add_argument("--disable_timeout", action="store_true", default=True, help="禁用超时终止")
    
    # 仿真参数
    sim_group = parser.add_argument_group('仿真参数')
    sim_group.add_argument("--sim_dt", type=float, default=0.005, help="仿真时间步长")
    sim_group.add_argument("--substeps", type=int, default=2, help="仿真子步数")
    
    # 性能优化参数
    perf_group = parser.add_argument_group('性能优化参数')
    perf_group.add_argument("--precision_mode", type=str, default="balanced", 
                           choices=["fast", "balanced", "precise"], help="精度模式")
    perf_group.add_argument("--disable_optimizations", action="store_true", help="禁用所有优化")


def print_env_config_info(env_cfg, args: argparse.Namespace):
    """打印环境配置信息
    
    Args:
        env_cfg: 环境配置
        args: 命令行参数
    """
    
    print("\n=== 环境配置信息 ===")
    print(f"任务名称: {getattr(env_cfg, 'env_name', 'Unknown')}")
    print(f"环境数量: {env_cfg.scene.num_envs}")
    print(f"环境间距: {env_cfg.scene.env_spacing}")
    print(f"物理复制: {env_cfg.scene.replicate_physics}")
    print(f"仿真时间步: {env_cfg.sim.dt}")
    print(f"Episode长度: {env_cfg.episode_length_s}s")
    print(f"控制频率: {1.0 / (env_cfg.sim.dt * env_cfg.decimation):.1f}Hz")
    print(f"精度模式: {getattr(args, 'precision_mode', 'unknown')}")
    print(f"优化状态: {'禁用' if getattr(args, 'disable_optimizations', False) else '启用'}")
    print("==================")


# 便捷函数
def setup_env_from_args(args: argparse.Namespace):
    """从命令行参数设置环境配置
    
    Args:
        args: 命令行参数
        
    Returns:
        tuple: (env_cfg, env)
    """
    import gymnasium as gym
    
    # 创建环境配置
    env_cfg = create_enhanced_env_cfg(args.task, args)
    
    # 打印配置信息
    if getattr(args, 'verbose', False):
        print_env_config_info(env_cfg, args)
    
    # 创建环境
    env = gym.make(args.task, cfg=env_cfg).unwrapped
    
    return env_cfg, env 