#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
# Mount the USB bus directory so the OAK's re-enumerated device remains visible.
exec docker compose --env-file .env.real run --rm --no-deps \
    -v /dev/bus/usb:/dev/bus/usb \
    xr oak-uvc "$@"
