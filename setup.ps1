# Builds the mark2-coppeliasim Docker image (CoppeliaSim + Xvfb + noVNC +
# Python remote-API client). Run this once (and again after editing
# docker/Dockerfile). Windows/PowerShell equivalent of setup.sh.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

docker build -t mark2-coppeliasim:latest ./docker
Write-Host "Image mark2-coppeliasim:latest built."
