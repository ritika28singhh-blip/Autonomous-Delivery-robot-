<!-- Animated Header Banner -->
<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20,30,40&height=220&section=header&text=Autonomous%20Indoor%20Robot&fontSize=32&animation=fadeIn&fontColor=ffffff&fontAlignY=38&desc=CoppeliaSim%20MVP%20%E2%80%A2%20Vision%20&%20Sensor%20Navigation&descSize=14&descAlignY=65" width="100%"/>
</p>

<!-- Live Status & Tech Badges -->
<p align="center">
  <img src="https://img.shields.io/badge/STATUS-ACTIVE%20%F0%9F%94%A5-success?style=for-the-badge&logo=none" alt="Status"/>
  <img src="https://img.shields.io/badge/SIMULATOR-CoppeliaSim-blue?style=for-the-badge&logo=robot&logoColor=white" alt="CoppeliaSim"/>
  <img src="https://img.shields.io/badge/CONTAINER-Docker-blueviolet?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/PYTHON-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
</p>

---

## 🤖 Overview
A minimal, end-to-end minimum viable prototype (MVP) of a mobile robot that navigates an indoor environment to deliver a parcel from point **A** to point **B**, built on **CoppeliaSim**. It utilizes an onboard camera for vision and a ring of proximity sensors for real-time obstacle avoidance. 

> **Note:** This project proves the full pipeline works end-to-end (scene generation → sensor integration → navigation logic → vision-confirmed delivery) rather than serving as a heavy production-grade stack.

---

## ⚡ Key Pipeline Capabilities

1. **Procedural Scene Generation (`build_scene.py`)**: Communicates with CoppeliaSim over the ZeroMQ Remote API to programmatically construct walls, rooms, furniture, start/goal markers, and the robot itself.
2. **Reactive Potential-Field Navigation (`controller.py`)**: Computes attractive vectors toward the goal combined with repulsive vectors from 8 proximity sensors to steer around obstacles smoothly.
3. **Vision-Confirmed Delivery**: Combines spatial coordinate proximity with OpenCV color thresholding on the onboard camera stream to visually verify the green goal beacon before declaring success.
4. **Headless Containerized Runtime**: Bundles CoppeliaSim, Xvfb virtual display, and an optional **noVNC** browser bridge inside Docker for cross-platform reproducibility.

---

## 🏗️ System Architecture

```mermaid
graph TD
    A[Docker Container: Xvfb + CoppeliaSim ZMQ API] -->|ZMQ RPC cbor| B[Python Controller Scripts]
    B --> C[build_scene.py: Generates Scene Graph]
    B --> D[controller.py: Sensors + Vision + Navigation]
    A --> E[:6080 noVNC Browser Stream]
