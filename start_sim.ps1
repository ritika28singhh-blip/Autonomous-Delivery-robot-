# Starts (or restarts) the mark2sim container: Xvfb virtual display,
# CoppeliaSim listening on the ZMQ remote API (port 23000), and a noVNC
# web viewer (port 6080) so you can watch the simulator live in a browser.
# Windows/PowerShell equivalent of start_sim.sh.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

docker rm -f mark2sim 2>$null | Out-Null

docker run -d --name mark2sim `
  -v "${PSScriptRoot}/scripts:/workspace/scripts" `
  -v "${PSScriptRoot}/scenes:/workspace/scenes" `
  -v "${PSScriptRoot}/logs:/workspace/logs" `
  -v "${PSScriptRoot}/videos:/workspace/videos" `
  -p 23000:23000 `
  -p 6080:6080 `
  mark2-coppeliasim:latest `
  bash -c "Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp & export DISPLAY=:99; sleep 2; exec /opt/coppeliasim/coppeliaSim -GzmqRemoteApi.rpcPort=23000"

Write-Host "Waiting for CoppeliaSim to come up..."
Start-Sleep -Seconds 6

# Start the VNC bridge only after CoppeliaSim's own X connection is
# established -- starting it earlier has been observed to destabilize
# CoppeliaSim's event loop under Xvfb + software (llvmpipe) rendering.
docker exec -d mark2sim bash -c "export DISPLAY=:99; x11vnc -display :99 -forever -shared -nopw -quiet -rfbport 5900 & websockify --web /usr/share/novnc 6080 localhost:5900 &"

Write-Host "mark2sim is up."
Write-Host "  ZMQ remote API: localhost:23000"
Write-Host "  Live view:      http://localhost:6080/vnc.html"
