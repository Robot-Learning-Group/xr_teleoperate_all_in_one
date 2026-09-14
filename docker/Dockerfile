# syntax=docker/dockerfile:1
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04 AS common

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV DEBIAN_FRONTEND=noninteractive \
    CONDA_DIR=/opt/conda \
    PATH=/opt/conda/bin:$PATH \
    OMNI_KIT_ALLOW_ROOT=1 \
    ACCEPT_EULA=Y \
    PRIVACY_CONSENT=Y \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility,video,graphics,display

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc-12 g++-12 cmake ca-certificates curl git git-lfs \
    libasound2 libegl1 libgl1 libglib2.0-0 libglu1-mesa-dev libnss3 \
    libsm6 libvulkan1 libx11-6 libx11-xcb1 libxcb1 libxcursor1 libxext6 \
    libxi6 libxinerama1 libxkbcommon-x11-0 libxmu6 libxrandr2 libxrender1 \
    libxt6 libusb-1.0-0-dev libturbojpeg0-dev openssl unzip vulkan-tools zenity && \
    update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 100 && \
    update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-12 100 && \
    rm -rf /var/lib/apt/lists/*

# Use the same Miniconda setup as the existing and official Dockerfiles.
RUN curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p /opt/conda && rm /tmp/miniconda.sh && \
    conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main && \
    conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r && \
    conda clean -afy

COPY docker/repos.lock /opt/xr-aio/repos.lock
# Shared DDS sources; application dependencies are fetched only in their target.
RUN <<'BASH'
set -euo pipefail
mkdir -p /workspace
git lfs install --skip-repo
while read -r name url revision; do
    [[ -z "$name" || "$name" == \#* ]] && continue
    case "$name" in
        cyclonedds|unitree_sdk2_python) ;;
        *) continue ;;
    esac
    [[ "$name" =~ ^[A-Za-z0-9_-]+$ && "$revision" =~ ^[0-9a-f]{40}$ ]] || {
        echo "Invalid repository entry: $name" >&2
        exit 1
    }
    repo="/workspace/$name"
    mkdir "$repo"
    git -C "$repo" init -q
    git -C "$repo" remote add origin "$url"
    git -C "$repo" fetch --depth 1 origin "$revision"
    git -C "$repo" checkout --detach FETCH_HEAD
    git -C "$repo" submodule update --init --recursive --depth 1
done < /opt/xr-aio/repos.lock
BASH

RUN cmake -S /workspace/cyclonedds -B /tmp/cyclonedds-build \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/opt/cyclonedds && \
    cmake --build /tmp/cyclonedds-build --parallel 4 --target install && \
    rm -rf /tmp/cyclonedds-build
ENV CYCLONEDDS_HOME=/opt/cyclonedds \
    CMAKE_PREFIX_PATH=/opt/cyclonedds \
    LD_LIBRARY_PATH=/opt/cyclonedds/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64

COPY docker/entrypoint.sh /opt/xr-aio/entrypoint.sh
RUN chmod +x /opt/xr-aio/entrypoint.sh
ENTRYPOINT ["/opt/xr-aio/entrypoint.sh"]

FROM common AS sim
RUN conda create -y -n unitree_sim_env python=3.11 pip && \
    conda install -y -n unitree_sim_env -c conda-forge \
      'libgcc-ng>=12' 'libstdcxx-ng>=12' && \
    conda clean -afy

RUN <<'BASH'
set -euo pipefail
mkdir -p /workspace
git lfs install --skip-repo
while read -r name url revision; do
    [[ -z "$name" || "$name" == \#* ]] && continue
    case "$name" in
        IsaacLab|sim-teleimager|brainco-description|unitree_ros) ;;
        *) continue ;;
    esac
    [[ "$name" =~ ^[A-Za-z0-9_-]+$ && "$revision" =~ ^[0-9a-f]{40}$ ]] || {
        echo "Invalid repository entry: $name" >&2
        exit 1
    }
    repo="/workspace/$name"
    mkdir "$repo"
    git -C "$repo" init -q
    git -C "$repo" remote add origin "$url"
    git -C "$repo" fetch --depth 1 origin "$revision"
    case "$name" in
        brainco-description) git -C "$repo" sparse-checkout set revo2_system ;;
        unitree_ros) git -C "$repo" sparse-checkout set robots/g1_with_brainco_hand ;;
    esac
    git -C "$repo" checkout --detach FETCH_HEAD
    git -C "$repo" submodule update --init --recursive --depth 1
done < /opt/xr-aio/repos.lock
BASH
# The IsaacLab commit in repos.lock selects torch 2.7.0 + CUDA 12.8 on x86_64.
RUN conda run --no-capture-output -n unitree_sim_env python -m pip install --upgrade pip && \
    conda run --no-capture-output -n unitree_sim_env python -m pip install \
      torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0 \
      --index-url https://download.pytorch.org/whl/cu128 && \
    conda run --no-capture-output -n unitree_sim_env python -m pip install \
      'isaacsim[all,extscache]==5.1.0' --extra-index-url https://pypi.nvidia.com
WORKDIR /workspace/IsaacLab
# Match the existing build's EULA input. Return the installer's status, not
# the SIGPIPE from yes when the installer finishes reading.
RUN set +o pipefail && \
    yes Yes | conda run --no-capture-output -n unitree_sim_env bash isaaclab.sh --install none
COPY unitree_sim_isaaclab/requirements.txt /workspace/unitree_sim_isaaclab/requirements.txt
RUN ln -s /workspace/sim-teleimager /workspace/unitree_sim_isaaclab/teleimager
RUN conda run --no-capture-output -n unitree_sim_env python -m pip install \
      -e /workspace/unitree_sdk2_python \
      -e /workspace/unitree_sim_isaaclab/teleimager \
      -r /workspace/unitree_sim_isaaclab/requirements.txt

# Apply the camera settings required by Unitree's Isaac Sim 5.1 guide.
RUN sed -i 's/type:.*/type: isaacsim/' /workspace/unitree_sim_isaaclab/teleimager/cam_config_server.yaml && \
    sed -i 's/image_shape:.*/image_shape: [480, 640]/' /workspace/unitree_sim_isaaclab/teleimager/cam_config_server.yaml

# Official USD assets are a separate Hugging Face download, included in the image.
# The upstream downloader runs only inside this new build directory.
WORKDIR /workspace/unitree_sim_isaaclab
COPY unitree_sim_isaaclab/fetch_assets.sh ./fetch_assets.sh
RUN bash fetch_assets.sh

# Sim teleimager also uses the existing ~/.config/xr_teleoperate TLS files.
RUN mkdir -p /root/.config/xr_teleoperate && \
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout /root/.config/xr_teleoperate/key.pem \
      -out /root/.config/xr_teleoperate/cert.pem \
      -subj "/C=JP/ST=Tokyo/L=Tokyo/O=Unitree/OU=XR/CN=localhost"

COPY unitree_sim_isaaclab /workspace/unitree_sim_isaaclab
CMD ["sim"]

FROM common AS teleop
RUN conda create -y -n tv python=3.10 pip pinocchio=3.1.0 numpy=1.26.4 -c conda-forge && \
    conda clean -afy

RUN <<'BASH'
set -euo pipefail
mkdir -p /workspace
git lfs install --skip-repo
while read -r name url revision; do
    [[ -z "$name" || "$name" == \#* ]] && continue
    case "$name" in
        televuer|teleimager|dex-retargeting) ;;
        *) continue ;;
    esac
    [[ "$name" =~ ^[A-Za-z0-9_-]+$ && "$revision" =~ ^[0-9a-f]{40}$ ]] || {
        echo "Invalid repository entry: $name" >&2
        exit 1
    }
    repo="/workspace/$name"
    mkdir "$repo"
    git -C "$repo" init -q
    git -C "$repo" remote add origin "$url"
    git -C "$repo" fetch --depth 1 origin "$revision"
    git -C "$repo" checkout --detach FETCH_HEAD
    git -C "$repo" submodule update --init --recursive --depth 1
done < /opt/xr-aio/repos.lock
BASH
COPY xr_teleoperate/requirements.txt /opt/xr-aio/xr-requirements.txt
# Pinocchio 3.1.0 is installed through Conda above, as in the official setup.
# Let dex-retargeting resolve its pip dependency on pin, as in the existing build.
RUN conda run --no-capture-output -n tv python -m pip install --upgrade pip && \
    conda run --no-capture-output -n tv python -m pip install \
      numpy==1.26.4 params-proto==2.13.0 \
      -e /workspace/unitree_sdk2_python \
      -e /workspace/televuer \
      -e '/workspace/teleimager[server]' \
      -e /workspace/dex-retargeting \
      -r /opt/xr-aio/xr-requirements.txt

COPY xr_teleoperate /workspace/xr_teleoperate
RUN test -f /workspace/xr_teleoperate/teleop/teleop_hand_and_arm.py

# Match the existing Docker setup: prepare certificates during the build.
RUN mkdir -p /root/.config/xr_teleoperate && \
    if [ -f /workspace/televuer/key.pem ] && [ -f /workspace/televuer/cert.pem ]; then \
      cp /workspace/televuer/key.pem /workspace/televuer/cert.pem /root/.config/xr_teleoperate/; \
    else \
      openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /root/.config/xr_teleoperate/key.pem \
        -out /root/.config/xr_teleoperate/cert.pem \
        -subj "/C=JP/ST=Tokyo/L=Tokyo/O=Unitree/OU=XR/CN=localhost"; \
    fi

WORKDIR /workspace
CMD ["shell"]
