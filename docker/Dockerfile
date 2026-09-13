# syntax=docker/dockerfile:1
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

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
    conda create -y -n unitree_sim_env python=3.11 pip && \
    conda install -y -n unitree_sim_env -c conda-forge \
      'libgcc-ng>=12' 'libstdcxx-ng>=12' && \
    conda create -y -n tv python=3.10 pip pinocchio=3.1.0 numpy=1.26.4 -c conda-forge && \
    conda clean -afy

COPY docker/repos.lock /opt/xr-aio/repos.lock
# Fetch all seven dependencies together, outside the editable XR directory.
RUN <<'BASH'
set -euo pipefail
mkdir -p /opt/src
git lfs install --skip-repo
while read -r name url revision; do
    [[ -z "$name" || "$name" == \#* ]] && continue
    [[ "$name" =~ ^[A-Za-z0-9_-]+$ && "$revision" =~ ^[0-9a-f]{40}$ ]] || {
        echo "Invalid repository entry: $name" >&2
        exit 1
    }
    repo="/opt/src/$name"
    mkdir "$repo"
    git -C "$repo" init -q
    git -C "$repo" remote add origin "$url"
    git -C "$repo" fetch --depth 1 origin "$revision"
    git -C "$repo" checkout --detach FETCH_HEAD
    git -C "$repo" submodule update --init --recursive --depth 1
done < /opt/xr-aio/repos.lock
BASH

RUN cmake -S /opt/src/cyclonedds -B /tmp/cyclonedds-build \
      -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/opt/cyclonedds && \
    cmake --build /tmp/cyclonedds-build --parallel 4 --target install && \
    rm -rf /tmp/cyclonedds-build
ENV CYCLONEDDS_HOME=/opt/cyclonedds \
    CMAKE_PREFIX_PATH=/opt/cyclonedds \
    LD_LIBRARY_PATH=/opt/cyclonedds/lib:/usr/local/nvidia/lib:/usr/local/nvidia/lib64

# The IsaacLab commit in repos.lock selects torch 2.7.0 + CUDA 12.8 on x86_64.
RUN conda run --no-capture-output -n unitree_sim_env python -m pip install --upgrade pip && \
    conda run --no-capture-output -n unitree_sim_env python -m pip install \
      torch==2.7.0 torchvision==0.22.0 torchaudio==2.7.0 \
      --index-url https://download.pytorch.org/whl/cu128 && \
    conda run --no-capture-output -n unitree_sim_env python -m pip install \
      'isaacsim[all,extscache]==5.1.0' --extra-index-url https://pypi.nvidia.com
WORKDIR /opt/src/IsaacLab
# Match the existing build's EULA input. Return the installer's status, not
# the SIGPIPE from yes when the installer finishes reading.
RUN set +o pipefail && \
    yes Yes | conda run --no-capture-output -n unitree_sim_env bash isaaclab.sh --install none
RUN conda run --no-capture-output -n unitree_sim_env python -m pip install \
      -e /opt/src/unitree_sdk2_python \
      -e /opt/src/unitree_sim_isaaclab/teleimager \
      -r /opt/src/unitree_sim_isaaclab/requirements.txt

# Apply the camera settings required by Unitree's Isaac Sim 5.1 guide.
RUN sed -i 's/type:.*/type: isaacsim/' /opt/src/unitree_sim_isaaclab/teleimager/cam_config_server.yaml && \
    sed -i 's/image_shape:.*/image_shape: [480, 640]/' /opt/src/unitree_sim_isaaclab/teleimager/cam_config_server.yaml

# Official USD assets are a separate Hugging Face download, included in the image.
# The upstream downloader runs only inside this new build directory.
WORKDIR /opt/src/unitree_sim_isaaclab
RUN bash fetch_assets.sh

COPY xr_teleoperate/requirements.txt /opt/xr-aio/xr-requirements.txt
# Pinocchio 3.1.0 is installed through Conda above, as in the official setup.
# Let dex-retargeting resolve its pip dependency on pin, as in the existing build.
RUN conda run --no-capture-output -n tv python -m pip install --upgrade pip && \
    conda run --no-capture-output -n tv python -m pip install \
      numpy==1.26.4 params-proto==2.13.0 \
      -e /opt/src/unitree_sdk2_python \
      -e /opt/src/televuer \
      -e '/opt/src/teleimager[server]' \
      -e /opt/src/dex-retargeting \
      -r /opt/xr-aio/xr-requirements.txt

# Copy editable code last so code-only rebuilds retain the dependency layers.
COPY xr_teleoperate /opt/src/xr_teleoperate
RUN test -f /opt/src/xr_teleoperate/teleop/teleop_hand_and_arm.py

# Match the existing Docker setup: prepare certificates during the build.
RUN mkdir -p /root/.config/xr_teleoperate && \
    if [ -f /opt/src/televuer/key.pem ] && [ -f /opt/src/televuer/cert.pem ]; then \
      cp /opt/src/televuer/key.pem /opt/src/televuer/cert.pem /root/.config/xr_teleoperate/; \
    else \
      openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /root/.config/xr_teleoperate/key.pem \
        -out /root/.config/xr_teleoperate/cert.pem \
        -subj "/C=JP/ST=Tokyo/L=Tokyo/O=Unitree/OU=XR/CN=localhost"; \
    fi

COPY docker/entrypoint.sh /opt/xr-aio/entrypoint.sh
RUN chmod +x /opt/xr-aio/entrypoint.sh
WORKDIR /opt/src
ENTRYPOINT ["/opt/xr-aio/entrypoint.sh"]
CMD ["shell"]
