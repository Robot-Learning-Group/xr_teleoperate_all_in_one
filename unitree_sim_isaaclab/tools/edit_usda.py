import re

def modify_instanceable_flag(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    modified_lines = []
    inside_visuals_block = False
    visuals_start_re = re.compile(r'^\s*def\s+Xform\s+"visuals"\s*\(')
    instanceable_re = re.compile(r'^\s*instanceable\s*=\s*true\s*$')
    # instanceable_re = re.compile(r'^\s*instanceable\s*=\s*false\s*$')

    for line in lines:
        if visuals_start_re.match(line):
            inside_visuals_block = True
            modified_lines.append(line)
            continue

        if inside_visuals_block:
            if instanceable_re.match(line):
                # Replace 'true' with 'false'
                modified_lines.append('            instanceable = false\n')
                # modified_lines.append('            instanceable = true\n')
            else:
                modified_lines.append(line)

            if line.strip().endswith(')'):
                inside_visuals_block = False
        else:
            modified_lines.append(line)

    # 保存修改后的内容
    with open('/home/unitree/newDisk/URDF/urdf-to-usd/h1_2_inspire/h1_2_demo2.usda', 'w', encoding='utf-8') as f:
        f.writelines(modified_lines)

# 使用方法
modify_instanceable_flag('/home/unitree/newDisk/URDF/urdf-to-usd/h1_2_inspire/demo.usda')  # 替换为你的实际文件路径
