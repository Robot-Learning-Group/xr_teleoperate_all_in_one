## Isaac Sim 5.0.0 Environment Installation

### 2.1 Clone the unitree_sim_isaaclab Repository
1. Clone the unitree_sim_isaaclab repository:
```
git clone git@github.com:unitreerobotics/unitree_sim_isaaclab.git
```
2. Initialize and clone the submodules:
```
cd unitree_sim_isaaclab
git submodule update --init --depth 1
```
3. Modify the teleimager configuration file (cam_config_server.yaml)

Update the corresponding keys in cam_config_server.yaml as follows:

```
image_shape: [480, 640]
type: isaacsim
```
Please refer to the teleimager[README.md](https://github.com/unitreerobotics/teleimager/blob/main/README.md)for detailed configuration instructions and environment setup.
### 2.2 Installation on Ubuntu 22.04 and Later(pip install)

- **Create Virtual Environment**

```
conda create -n unitree_sim_env python=3.11
conda activate unitree_sim_env
```
- **Install Pytorch**

This needs to be installed according to your CUDA version. Please refer to the [official PyTorch installation guide](https://pytorch.org/get-started/locally/). The following example uses CUDA 12:

```
pip install torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0 --index-url https://download.pytorch.org/whl/cu126
```
- **Install Isaac Sim 5.0.0**

```
pip install --upgrade pip

pip install "isaacsim[all,extscache]==5.0.0" --extra-index-url https://pypi.nvidia.com
```
Verify successful installation:
```
isaacsim
```
First execution will show: Do you accept the EULA? (Yes/No):  Yes

-  **Install Isaac Lab**

```
git clone git@github.com:isaac-sim/IsaacLab.git

sudo apt install cmake build-essential

cd IsaacLab

git checkout v2.2.0

./isaaclab.sh --install 

```

Verify successful installation:
```
python scripts/tutorials/00_sim/create_empty.py
or
./isaaclab.sh -p scripts/tutorials/00_sim/create_empty.py
```

- **Install unitree_sdk2_python**

```
git clone https://github.com/unitreerobotics/unitree_sdk2_python

cd unitree_sdk2_python

pip3 install -e .
```

- **Install other dependencies**
```
pip install -r requirements.txt
```

### 2.3 Installation on Ubuntu 20.04(binary install)

- **Download Isaac Sim Binary**

Download the [Isaac Sim 5.0.0 binary](https://docs.isaacsim.omniverse.nvidia.com/latest/installation/download.html#download-isaac-sim-shortl) and extract it.

Assume the path to Isaac Sim is ``/home/unitree/tools/isaac-sim``. Follow the steps below:

- **Set environment variables**

Please replace with your own path

```
export ISAACSIM_PATH="${HOME}/tools/isaac-sim"            
export ISAACSIM_PYTHON_EXE="${ISAACSIM_PATH}/python.sh"  
```
Verify the setup:
```
${ISAACSIM_PATH}/isaac-sim.sh
# or
${ISAACSIM_PYTHON_EXE} -c "print('Isaac Sim configuration is now complete.')"

Note: All conda environments (including base) must be deactivated before running this.
```
**Note:** You can add the above commands to your ~/.bashrc file for convenience.

- **Install Isaac Lab**

```
git clone git@github.com:isaac-sim/IsaacLab.git

sudo apt install cmake build-essential

cd IsaacLab

git checkout v2.2.0

ln -s ${HOME}/tools/isaac-sim/ _isaac_sim     (Please replace with your own path)

./isaaclab.sh --conda unitree_sim_env

conda activate unitree_sim_env

./isaaclab.sh --install

```

- **Install unitree_sdk2_python**

```
git clone https://github.com/unitreerobotics/unitree_sdk2_python

cd unitree_sdk2_python

pip3 install -e .

```

- **Install other dependencies**

```
pip install -r requirements.txt

cd teleimager

pip install -e .
```

**Problem:**

* 1 `libstdc++.so.6` version is too low

```
OSError: /home/unitree/tools/anaconda3/envs/env_isaaclab_tem/bin/../lib/libstdc++.so.6: version GLIBCXX_3.4.30' not found (required by /home/unitree/tools/anaconda3/envs/env_isaaclab_tem/lib/python3.11/site-packages/omni/libcarb.so)
```
**Solution:**
`conda install -c conda-forge libstdcxx-ng`

*  2 Installation Issue with `unitree_sdk2_python`

If you encounter the following error when installing `unitree_sdk2_python`:

```
Could not locate cyclonedds. Try to set CYCLONEDDS_HOME or CMAKE_PREFIX_PATH
```

or

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

**Solution**: Please refer to the [unitree\_sdk2\_python FAQ](https://github.com/unitreerobotics/unitree_sdk2_python?tab=readme-ov-file#faq) for instructions.
