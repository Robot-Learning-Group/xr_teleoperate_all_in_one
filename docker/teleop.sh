#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

# Simulation: G1_29 + Dex3, controller tracking, recording enabled.
# Edit the Python arguments below to change the startup settings.
exec docker compose run --rm xr shell -c '
    set -euo pipefail
    network_args=()
    if [[ -n ${NETWORK_INTERFACE:-} ]]; then
        network_args=(--network-interface "$NETWORK_INTERFACE")
    fi
    exec python teleop_hand_and_arm.py \
        --sim \
        --headless \
        --input-mode controller \
        --arm G1_29 \
        --ee dex3 \
        --record \
        --img-server-ip "$IMG_SERVER_IP" \
        "${network_args[@]}" "$@"
' bash "$@"
