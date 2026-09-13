#!/bin/bash

set -e  # 脚本执行报错时立即退出
set -o pipefail

REPO_NAME="unitree_sim_isaaclab_usds"

# 1. 预清理：如果目标文件夹已存在，先删除
if [ -d "$REPO_NAME" ]; then
    echo "Warning: Directory '$REPO_NAME' already exists. Removing it for a fresh clone..."
    rm -rf "$REPO_NAME"
fi

# 2. 克隆仓库
echo "Cloning repository..."
git lfs install
git clone "https://huggingface.co/datasets/unitreerobotics/$REPO_NAME"

# 3. 进入目录
cd "$REPO_NAME"

# 4. 检查 assets.zip 是否存在且大于 1GB
if [ ! -f "assets.zip" ]; then
    echo "Error: assets.zip does not exist"
    exit 1
fi

filesize=$(stat -c%s "assets.zip")
if [ "$filesize" -le $((1024 * 1024 * 1024)) ]; then
    echo "Error: assets.zip is less than 1GB. Check Git LFS status."
    exit 1
fi

echo "assets.zip check passed, size is $((filesize / 1024 / 1024)) MB"

# 5. 解压 assets.zip
echo "Unzipping assets.zip..."
unzip -q assets.zip

# 6. 处理父目录中的 assets 文件夹并移动
if [ -d "assets" ]; then
    # 检查父目录（..）是否已经存在 assets 文件夹，存在则删除
    if [ -d "../assets" ]; then
        echo "Cleaning up existing '../assets' folder..."
        rm -rf "../assets"
    fi

    echo "Moving new assets to parent directory..."
    mv assets ../
else
    echo "Error: assets unzip failed or folder does not exist"
    exit 1
fi

# 7. 返回上级并清理临时仓库
cd ..
echo "Deleting temporary folder '$REPO_NAME'..."
rm -rf "$REPO_NAME"

echo "✅ All done! Assets have been successfully updated."