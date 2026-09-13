## Isaac Sim 5.0.0环境安装


### 2.1 克隆unitree_sim_isaaclab仓库
1. 克隆unitree_sim_isaaclab仓库
```
git clone git@github.com:unitreerobotics/unitree_sim_isaaclab.git
```
2. 克隆子项目
```
cd unitree_sim_isaaclab
git submodule update --init --depth 1
```
3. 修改teleimager配置文件(cam_config_server.yaml)

按照下面的内容修改 cam_config_server.yaml中的对应的key
```
image_shape: [480, 640]
type: isaacsim
```
请参考teleimager的[README.md](https://github.com/unitreerobotics/teleimager/blob/main/README.md)进行配置以及环境安装

### 2.2 Ubuntu 22.04 以及以上的安装(pip install)

-  创建虚拟环境

```
conda create -n unitree_sim_env python=3.11
conda activate unitree_sim_env
```
- 安装Pytorch

这个需要根据自己的CUDA版本进行安装，具体参考[Pytorch官方教程](https://pytorch.org/get-started/locally/),下面以CUDA 12为例进行安装

```
pip install torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0 --index-url https://download.pytorch.org/whl/cu126
```
-  安装 Isaac Sim 5.0.0

```
pip install --upgrade pip

pip install "isaacsim[all,extscache]==5.0.0" --extra-index-url https://pypi.nvidia.com

```
验证是否安装成功
```
isaacsim
```
第一次执行会有:Do you accept the EULA? (Yes/No):  Yes



- 安装Isaac Lab

```
git clone git@github.com:isaac-sim/IsaacLab.git

sudo apt install cmake build-essential

cd IsaacLab

git checkout v2.2.0

./isaaclab.sh --install 

```

验证安装是否成功
```
python scripts/tutorials/00_sim/create_empty.py
or
./isaaclab.sh -p scripts/tutorials/00_sim/create_empty.py
```

- 安装unitree_sdk2_python

```
git clone https://github.com/unitreerobotics/unitree_sdk2_python

cd unitree_sdk2_python

pip3 install -e .
```
- 安装其他依赖
```
pip install -r requirements.txt
```

### 2.3 Ubuntu 20.4安装(二进制安装)

- 下载二进制的Isaaac Sim

下载对应版本的
[二进制Isaac Sim 5.0.0](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/download.html#download-isaac-sim-short)并解压；

假设isaac sim放在`/home/unitree/tools/isaac-sim`,请按照下面的步骤进行安装；

- 设在环境变量

```
export ISAACSIM_PATH="${HOME}/tools/isaac-sim"

export ISAACSIM_PYTHON_EXE="${ISAACSIM_PATH}/python.sh"

```
测试设置是否成功

```
${ISAACSIM_PATH}/isaac-sim.sh

或

${ISAACSIM_PYTHON_EXE} -c "print('Isaac Sim configuration is now complete.')" 

需要退出包括base在内的所有的conda环境

```

**注意：** 可以把上面命令写到bashrc文件中

- 安装 Isaac Lab

```
git clone git@github.com:isaac-sim/IsaacLab.git

sudo apt install cmake build-essential

cd IsaacLab

git checkout v2.2.0

ln -s ${HOME}/tools/isaac-sim/ _isaac_sim     (请根据自己路径填写)

./isaaclab.sh --conda unitree_sim_env

conda activate  unitree_sim_env

./isaaclab.sh --install

```

- 安装 unitree_sdk2_python

```
git clone https://github.com/unitreerobotics/unitree_sdk2_python

cd unitree_sdk2_python

pip3 install -e .

```

- 安装其他的依赖

```
pip install -r requirements.txt

cd teleimager

pip install -e .

```


**问题:**
- 1 libstdc++.so.6版本低
```
OSError: /home/unitree/tools/anaconda3/envs/env_isaaclab_tem/bin/../lib/libstdc++.so.6: version GLIBCXX_3.4.30' not found (required by /home/unitree/tools/anaconda3/envs/env_isaaclab_tem/lib/python3.11/site-packages/omni/libcarb.so)
```
解决: conda install -c conda-forge libstdcxx-ng

- 2 安装unitree_sdk2_python 问题

如果在安装unitree_sdk2_python 遇到以下问题

```
Could not locate cyclonedds. Try to set CYCLONEDDS_HOME or CMAKE_PREFIX_PATH

```
或

```
Collecting cyclonedds==0.10.2 (from unitree_sdk2py==1.0.1)
  Downloading cyclonedds-0.10.2.tar.gz (156 kB)
  Installing build dependencies ... done
  Getting requirements to build wheel ... error
  error: subprocess-exited-with-error
  
  × Getting requirements to build wheel did not run successfully.
  │ exit code: 1
  ╰─> [1 lines of output]
      Could not locate cyclonedds. Try to set CYCLONEDDS_HOME or CMAKE_PREFIX_PATH
      [end of output]
  
  note: This error originates from a subprocess, and is likely not a problem with pip.
error: subprocess-exited-with-error

× Getting requirements to build wheel did not run successfully.
│ exit code: 1
╰─> See above for output.

note: This error originates from a subprocess, and is likely not a problem with pip.
```
解决: 请参考[unitree_sdk2_python FAQ](https://github.com/unitreerobotics/unitree_sdk2_python?tab=readme-ov-file#faq)

