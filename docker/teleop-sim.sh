#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

xauthority=${XAUTHORITY:-$HOME/.Xauthority}
if [[ -z ${DISPLAY:-} || ! -r $xauthority ]]; then
    echo "Rerun requires DISPLAY and a readable XAUTHORITY file. Run from a desktop terminal." >&2
    exit 1
fi

# Simulation teleoperation: G1_29 + Dex3, controller tracking, recording enabled.
# Edit the Python arguments below to change the startup settings.
exec docker compose --env-file .env.sim run --rm \
    -e DISPLAY="$DISPLAY" \
    -e XAUTHORITY=/tmp/xr.Xauthority \
    -v /tmp/.X11-unix:/tmp/.X11-unix:ro \
    -v "$xauthority:/tmp/xr.Xauthority:ro" \
    xr shell -c '
    set -euo pipefail
    network_args=()
    if [[ -n ${NETWORK_INTERFACE:-} ]]; then
        network_args=(--network-interface "$NETWORK_INTERFACE")
    fi
    exec python teleop_hand_and_arm.py \
        --sim \
        --input-mode controller \
        --display-mode pass-through \
        --arm G1_29 \
        --ee dex3 \
        --record \
        --img-server-ip "$IMG_SERVER_IP" \
        "${network_args[@]}" "$@"
' bash "$@"
