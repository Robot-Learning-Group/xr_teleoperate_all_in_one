#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
from typing import List, Set, Optional
from pathlib import Path
import re

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def modify_usda_file(input_file, output_file, target_links):
    """
    修改usda文件
    - 所有visuals下的instanceable改为false
    - 指定link下的collisions的instanceable改为false
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    modified_lines = []
    current_link = None
    inside_visuals_block = False
    inside_collisions_block = False
    find_target_link = False
    
    # 编译正则表达式
    visuals_start_re = re.compile(r'^\s*def\s+Xform\s+"visuals"\s*\(')
    collisions_start_re = re.compile(r'\s*def\s+Xform\s+"collisions"\s*\(')
    instanceable_re = re.compile(r'^\s*instanceable\s*=\s*true\s*$')
    collisions_instanceable_re = re.compile(r'^\s*instanceable\s*=\s*true\s*$')
    
    for line in lines:
        # 检查是否是Xform定义行
        if 'def Xform "' in line:
            if visuals_start_re.match(line):
                inside_visuals_block = True
                modified_lines.append(line)
                continue
            elif collisions_start_re.match(line):
                inside_collisions_block = True
                modified_lines.append(line)
                continue
            else:
                # 提取link名称
                current_link = line.split('"')[1]
                
                if current_link in target_links:
                    find_target_link = True
                    inside_collisions_block = False
                    inside_visuals_block = False
                modified_lines.append(line)
                continue
        # 处理visuals部分
        if inside_visuals_block:
            if instanceable_re.match(line):
                modified_lines.append('            instanceable = false\n')
            else:
                modified_lines.append(line)
            if line.strip().endswith(')'):
                inside_visuals_block = False
            continue
        # 处理collisions部分
        if inside_collisions_block and find_target_link:
            if  instanceable_re.match(line):
                modified_lines.append('            instanceable = false\n')
            else:
                modified_lines.append(line)
            if line.strip().endswith(')'):
                inside_collisions_block = False
                find_target_link = False
            continue
        # 其他行直接添加
        else:
            modified_lines.append(line)
            continue

    # 保存修改后的内容
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(modified_lines)

def main():
    """主函数"""
    # 使用方法
    target_links = [
        "right_hand_index_0_link", 
        "right_hand_index_1_link",
        "right_hand_middle_0_link",
        "right_hand_middle_1_link",
        "right_hand_thumb_0_link",
        "right_hand_thumb_1_link",
        "right_hand_thumb_2_link",
        "left_hand_index_0_link", 
        "left_hand_index_1_link",
        "left_hand_middle_0_link",
        "left_hand_middle_1_link",
        "left_hand_thumb_0_link",
        "left_hand_thumb_1_link",
        "left_hand_thumb_2_link",

        
    ]
    
    input_file = "/home/unitree/newDisk/URDF/urdf-to-usd/g1withdex3/g1_29dof_with_hand_rev_1_0.usda"
    output_file = "/home/unitree/newDisk/URDF/urdf-to-usd/g1withdex3/g1_29dof_with_hand_rev_1_0_edit.usda"
    
    try:
        modify_usda_file(input_file, output_file, target_links)
        logger.info(f"文件处理完成，已保存到: {output_file}")
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
