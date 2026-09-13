#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

# Real G1_29: controller tracking, arms only, recording enabled.
# Edit the Python arguments below to change the startup settings.
exec docker compose run --rm xr shell -c '
    set -euo pipefail
    network_args=()
    if [[ -n ${NETWORK_INTERFACE:-} ]]; then
        network_args=(--network-interface "$NETWORK_INTERFACE")
    fi
    exec python teleop_hand_and_arm.py \
        --headless \
        --input-mode controller \
        --arm G1_29 \
        --record \
        --img-server-ip "$IMG_SERVER_IP" \
        "${network_args[@]}" "$@"
' bash "$@"
