#!/usr/bin/env bash
# Builds the mark2-coppeliasim Docker image (CoppeliaSim + Xvfb + noVNC +
# Python remote-API client). Run this once (and again after editing
# docker/Dockerfile).
set -euo pipefail
cd "$(dirname "$0")"

docker build -t mark2-coppeliasim:latest ./docker
echo "Image mark2-coppeliasim:latest built."
