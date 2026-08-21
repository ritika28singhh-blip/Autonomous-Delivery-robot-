# Builds the delivery scene and runs the navigation controller inside the
# already-running mark2sim container. Requires start_sim.ps1 to have been
# run first. Windows/PowerShell equivalent of run_demo.sh.
#
# Usage: .\run_demo.ps1 [maxTimeSeconds]
param(
    [int]$MaxTime = 60
)
$ErrorActionPreference = "Stop"

docker exec -w /workspace/scripts mark2sim python3 -u run_demo.py --max-time $MaxTime
