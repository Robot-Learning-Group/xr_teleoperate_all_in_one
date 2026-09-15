#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

# Simulation: G1_29, cylinder task. Defaults to Dex3.
ee=dex3
sim_args=()
while (($#)); do
    case "$1" in
        --ee)
            if (($# < 2)) || [[ "$2" == -* ]]; then
                echo "--ee requires dex3 or brainco." >&2
                exit 2
            fi
            ee=$2
            shift 2
            ;;
        --ee=*)
            ee=${1#--ee=}
            shift
            ;;
        *)
            sim_args+=("$1")
            shift
            ;;
    esac
done

case "$ee" in
    dex3) sim_command=sim ;;
    brainco) sim_command=sim-brainco ;;
    *)
        echo "Unsupported --ee: $ee. Choose dex3 or brainco." >&2
        exit 2
        ;;
esac

exec docker compose run --rm sim "$sim_command" "${sim_args[@]}"
