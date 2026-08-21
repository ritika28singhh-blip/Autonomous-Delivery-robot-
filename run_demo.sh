#!/usr/bin/env bash
# Builds the delivery scene and runs the navigation controller inside the
# already-running mark2sim container. Requires start_sim.sh to have been
# run first.
set -euo pipefail
MAX_TIME="${1:-60}"

docker exec -w /workspace/scripts mark2sim python3 -u run_demo.py --max-time "$MAX_TIME"
