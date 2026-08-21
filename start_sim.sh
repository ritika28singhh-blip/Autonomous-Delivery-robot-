#!/usr/bin/env bash
# Starts (or restarts) the mark2sim container: Xvfb virtual display,
# CoppeliaSim listening on the ZMQ remote API (port 23000), and a noVNC
# web viewer (port 6080) so you can watch the simulator live in a browser.
set -euo pipefail
cd "$(dirname "$0")"

docker rm -f mark2sim >/dev/null 2>&1 || true

docker run -d --name mark2sim \
  -v "$(pwd)/scripts:/workspace/scripts" \
  -v "$(pwd)/scenes:/workspace/scenes" \
  -v "$(pwd)/logs:/workspace/logs" \
  -v "$(pwd)/videos:/workspace/videos" \
  -p 23000:23000 \
  -p 6080:6080 \
  mark2-coppeliasim:latest \
  bash -c "Xvfb :99 -screen 0 1280x1024x24 -nolisten tcp & export DISPLAY=:99; sleep 2; exec /opt/coppeliasim/coppeliaSim -GzmqRemoteApi.rpcPort=23000"

echo "Waiting for CoppeliaSim to come up..."
sleep 6

# Start the VNC bridge only after CoppeliaSim's own X connection is
# established -- starting it earlier has been observed to destabilize
# CoppeliaSim's event loop under Xvfb + software (llvmpipe) rendering.
docker exec -d mark2sim bash -c \
  "export DISPLAY=:99; x11vnc -display :99 -forever -shared -nopw -quiet -rfbport 5900 & websockify --web /usr/share/novnc 6080 localhost:5900 &"

echo "mark2sim is up."
echo "  ZMQ remote API: localhost:23000"
echo "  Live view:      http://localhost:6080/vnc.html"
