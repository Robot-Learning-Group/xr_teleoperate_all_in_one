#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
# Start after oak-uvc.sh has exposed the OAK as /dev/videoX.
shopt -s nullglob
video_devices=(/dev/video*)
if ((${#video_devices[@]} == 0)); then
    echo "No /dev/video* devices found. Start oak-uvc.sh first." >&2
    exit 1
fi
device_args=()
for device in "${video_devices[@]}"; do
    device_args+=(-v "$device:$device")
done
exec docker compose --env-file .env.real run --rm --no-deps \
    "${device_args[@]}" -v /dev/bus/usb:/dev/bus/usb \
    xr image-server "$@"
