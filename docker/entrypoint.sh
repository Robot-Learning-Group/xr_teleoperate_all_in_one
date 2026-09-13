#!/usr/bin/env bash
set -euo pipefail

command=${1:-shell}
if (($#)); then shift; fi
source /opt/conda/etc/profile.d/conda.sh

case "$command" in
    sim)
        conda activate unitree_sim_env
        cd /opt/src/unitree_sim_isaaclab
        exec python sim_main.py --device cpu --headless --enable_cameras \
            --task Isaac-PickPlace-Cylinder-G129-Dex3-Joint \
            --enable_dex3_dds --robot_type g129 "$@"
        ;;
    teleop|teleop-real)
        conda activate tv
        cd /opt/src/xr_teleoperate/teleop
        network_args=()
        if [[ -n ${NETWORK_INTERFACE:-} ]]; then
            network_args=(--network-interface "$NETWORK_INTERFACE")
        fi
        mode_args=()
        if [[ "$command" == teleop ]]; then
            mode_args=(--sim)
        fi
        exec python teleop_hand_and_arm.py --input-mode hand --arm G1_29 \
            --ee dex3 --headless "${mode_args[@]}" \
            --img-server-ip "${IMG_SERVER_IP:-127.0.0.1}" \
            "${network_args[@]}" "$@"
        ;;
    image-server|image-server-cf)
        conda activate tv
        cd /opt/src/teleimager
        camera_args=()
        if [[ "$command" == image-server-cf ]]; then
            camera_args=(--cf)
        fi
        exec teleimager-server "${camera_args[@]}" "$@"
        ;;
    shell|sim-shell)
        if [[ "$command" == sim-shell ]]; then
            conda activate unitree_sim_env
            cd /opt/src/unitree_sim_isaaclab
        else
            conda activate tv
            cd /opt/src/xr_teleoperate/teleop
        fi
        exec bash "$@"
        ;;
    *)
        echo "Usage: $0 {sim|teleop|teleop-real|image-server|image-server-cf|shell|sim-shell} [arguments...]" >&2
        exit 2
        ;;
esac
