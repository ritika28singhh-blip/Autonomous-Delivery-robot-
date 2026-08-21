# Autonomous Indoor Delivery Robot — CoppeliaSim MVP

A minimal, end-to-end simulation of a mobile robot that navigates an
indoor environment using an onboard camera (vision) and a ring of
proximity sensors (obstacle avoidance) to deliver a "parcel" from point
**A** to point **B**, built on [CoppeliaSim](https://www.coppeliarobotics.com/).

This is a **minimum viable prototype**, not a polished product: the goal
was to prove the full pipeline works end-to-end (scene → sensors → nav
logic → vision-confirmed delivery), not to build a production-grade
navigation stack. See [Known limitations](#known-limitations) for what's
intentionally left out.

---

## Table of contents

- [What this actually does](#what-this-actually-does)
- [Architecture](#architecture)
- [Glossary / terms used in this repo](#glossary--terms-used-in-this-repo)
- [Project layout](#project-layout)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the demo](#running-the-demo)
- [Watching it live](#watching-it-live)
- [How the navigation actually works](#how-the-navigation-actually-works)
- [How "delivery" is detected](#how-delivery-is-detected)
- [Configuration knobs](#configuration-knobs)
- [Known limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)
- [License note](#license-note)

---

## What this actually does

1. A Python script (`build_scene.py`) talks to a running CoppeliaSim
   instance over its ZeroMQ Remote API and **programmatically constructs**
   a scene: a two-room floor plan connected by a doorway, a handful of box
   "furniture" obstacles, a start marker at point A, a green goal
   marker/beacon at point B, and the robot itself (body + camera + 8
   proximity sensors). No `.ttt` scene file is hand-edited — the scene is
   code, so it's fully reproducible and diffable.
2. A second script (`controller.py`) connects to the same simulator,
   starts the simulation, and every tick:
   - reads the 8 proximity sensors and computes a **repulsive** vector
     away from anything nearby (obstacle avoidance),
   - computes an **attractive** vector toward the known goal coordinate
     (stands in for what a real robot would get from indoor
     localization/SLAM),
   - combines both into a heading + speed command and moves the robot,
   - reads the onboard camera and checks (via OpenCV color thresholding)
     whether the **green goal marker** is in view,
   - declares "parcel delivered" only when the robot is both close to B
     **and** can visually confirm the marker — i.e. delivery is
     vision-confirmed, not just a position check.
3. Everything runs inside a Docker container (CoppeliaSim has no
   lightweight pip-installable form), with a virtual display (Xvfb) so it
   works in headless/CI-style environments, plus an optional noVNC bridge
   so you can actually *watch* the simulator's real window live in a
   browser.

## Architecture

```
┌─────────────────────────── Docker container (mark2sim) ───────────────────────────┐
│                                                                                     │
│   Xvfb :99 (virtual display) ── x11vnc ── websockify/noVNC ──▶ :6080 (browser)      │
│        │                                                                            │
│        ▼                                                                            │
│   CoppeliaSim  ── ZMQ Remote API server (Lua add-on) ──▶ :23000 (TCP)               │
│        │  scene graph: floor, walls, obstacles,                                     │
│        │  markers, robot body, vision sensor,                                       │
│        │  8x proximity sensors                                                      │
│        ▼                                                                            │
└──────────────────────────────────────┬──────────────────────────────────────────────┘
                                        │ ZMQ (cbor-encoded RPC)
                                        ▼
                     ┌──────────────────────────────────────┐
                     │   Python control process (host or     │
                     │   `docker exec` into the container)   │
                     │                                        │
                     │   build_scene.py  → constructs scene   │
                     │   controller.py   → reads sensors/cam, │
                     │                     runs potential-    │
                     │                     field navigation,  │
                     │                     writes video       │
                     │   run_demo.py     → runs both in one   │
                     │                     ZMQ connection     │
                     └──────────────────────────────────────┘
```

Why Docker at all? CoppeliaSim is a full desktop application (Qt-based,
~700MB installed), not a pip package. Running it in a container with a
virtual display makes the whole thing reproducible on any machine with
Docker — no local CoppeliaSim install, no GPU/X-server dependency on the
host, and no state left behind on your machine besides the image.

## Glossary / terms used in this repo

| Term | Meaning here |
|---|---|
| **ZMQ Remote API** | CoppeliaSim's scripting interface exposed over ZeroMQ. The Python client (`coppeliasim_zmqremoteapi_client`) sends RPC calls (`sim.createPrimitiveShape`, `sim.getObjectPosition`, ...) that execute inside CoppeliaSim's Lua environment and return results. This is how `build_scene.py`/`controller.py` control the simulator without writing any Lua. |
| **Xvfb** | "X virtual framebuffer" — a fake X11 display server that exists only in memory. Lets a GUI app like CoppeliaSim run without a physical monitor. |
| **noVNC / x11vnc** | `x11vnc` shares the Xvfb display over the VNC protocol; `websockify` + `noVNC` wrap that VNC stream so it can be viewed from a plain web browser at `http://localhost:6080/vnc.html`, no VNC client needed. |
| **Proximity sensor (ray type)** | A CoppeliaSim sensor that casts a ray and reports the distance to the first thing it hits (or "nothing detected"). 8 of these are mounted around the robot body, evenly spaced, forming a simple obstacle-detection ring — a much simpler stand-in for a full lidar. |
| **Vision sensor** | CoppeliaSim's camera object. `controller.py` reads its image buffer, converts to HSV, and thresholds for green to detect the goal beacon — real (if simple) computer vision, not a ground-truth cheat. |
| **Potential field navigation** | A classic reactive robotics technique: treat the goal as attracting the robot and obstacles as repelling it, sum the vectors each tick, and steer along the result. Simple, no path planning/map required, works well for open-ish indoor layouts. This is *not* SLAM or A\* — see [Known limitations](#known-limitations). |
| **Kinematic movement** | The robot's pose (x, y, yaw) is updated directly each tick from an integrated unicycle model (`x += speed*cos(yaw)*dt`, etc.) rather than being driven by physics/wheel joints. Chosen deliberately for this MVP — see below. |
| **Point A / Point B** | Hardcoded world coordinates in `build_scene.py`/`controller.py` (`POINT_A`, `POINT_B` / `GOAL`) representing the pickup and delivery locations. |

## Project layout

```
.
├── README.md
├── setup.sh / setup.ps1              # builds the Docker image
├── start_sim.sh / start_sim.ps1       # starts the container (CoppeliaSim + Xvfb + noVNC)
├── run_demo.sh / run_demo.ps1          # runs the scene-build + navigation inside it
├── .gitignore
├── docker/
│   └── Dockerfile          # Ubuntu 22.04 + CoppeliaSim + Xvfb + noVNC + Python deps
├── scripts/
│   ├── build_scene.py      # procedurally builds the delivery scene
│   ├── controller.py       # navigation + vision + delivery-confirmation logic
│   └── run_demo.py         # runs build_scene + controller over one connection
├── scenes/                 # generated .ttt scene files land here (gitignored)
├── videos/                 # generated run recordings land here (gitignored)
└── logs/                   # reserved for future run logs (gitignored)
```

## Windows

This runs the same way on Windows via **Docker Desktop** (WSL2 backend
recommended) — the container itself is Linux-based (`ubuntu:22.04`), so
nothing in the `Dockerfile` changes, and `localhost:6080` /
`localhost:23000` work the same in a normal Windows browser.

The only difference is which scripts to run:

| Environment | Use |
|---|---|
| WSL2 terminal, Git Bash, macOS, Linux | `setup.sh`, `start_sim.sh`, `run_demo.sh` |
| Native PowerShell (no WSL2/Git Bash) | `setup.ps1`, `start_sim.ps1`, `run_demo.ps1` |

```powershell
.\setup.ps1
.\start_sim.ps1
.\run_demo.ps1 90     # optional max-seconds argument
```

Both sets of scripts do exactly the same thing; use whichever matches
your shell.

## Prerequisites

- Docker (with the ability to run containers; no GPU required —
  rendering uses software/`llvmpipe`)
- ~1.5GB free disk (CoppeliaSim itself is ~700MB installed, plus the
  Ubuntu base image and Python deps)
- A browser, if you want to watch the run live via noVNC
- Internet access at *build* time only (the Dockerfile downloads
  CoppeliaSim EDU from `downloads.coppeliarobotics.com`)

## Setup

```bash
./setup.sh
```

This builds the `mark2-coppeliasim:latest` Docker image: Ubuntu 22.04 +
CoppeliaSim EDU 4.6.0 + Xvfb + x11vnc/noVNC + the Python packages
(`coppeliasim-zmqremoteapi-client`, `opencv-python-headless`, `numpy`,
`pyzmq`). Takes a few minutes the first time (mostly downloading
CoppeliaSim); subsequent builds are cached.

## Running the demo

```bash
./start_sim.sh      # starts the container: CoppeliaSim + ZMQ API + noVNC
./run_demo.sh        # builds the scene and runs the robot from A to B
```

`run_demo.sh` accepts an optional max simulated-time argument (seconds,
default 60):

```bash
./run_demo.sh 90
```

Expected output (abridged):

```
Scene saved to /workspace/scenes/delivery_demo.ttt
Scene built. Robot handle=32, camera handle=33, sensors=8
Point A (start) = (-3.3, 3.3, 0.0), Point B (goal) = (3.2, -3.3, 0.0)
[t=  0.1s] pos=(-3.28,3.30) dist_to_B=9.26m green_ratio=0.000
...
[t= 29.2s] Parcel DELIVERED at B (dist=0.08m, green_ratio=0.312)
```

A recording of the robot's onboard camera view is written to
`videos/delivery_run.mp4`.

Note: because rendering runs in software (no GPU in the container),
simulated time runs noticeably slower than wall-clock time — a ~30s
simulated run can take several minutes of real time. This is expected.

To run individual pieces directly instead of the combined wrapper:

```bash
docker exec -w /workspace/scripts mark2sim python3 build_scene.py
docker exec -w /workspace/scripts mark2sim python3 controller.py --max-time 60
```

(`run_demo.py` is preferred because it does both over a *single* ZMQ
connection — see [Troubleshooting](#troubleshooting) for why that
matters.)

## Watching it live

After `./start_sim.sh`, open:

```
http://localhost:6080/vnc.html
```

and click **Connect** (no password). You'll see CoppeliaSim's actual
window — the scene as it's built, and the robot moving live as
`run_demo.sh` executes. This is a real VNC session over a websocket, not
a screen-share hack, so it works through most port-forwarding setups
(e.g. VS Code's forwarded-ports panel) without extra configuration.

## How the navigation actually works

Every control tick (`DT = 0.05s` of wall-clock pacing) in
`controller.py`:

1. **Attraction**: a unit vector from the robot toward `GOAL`, scaled by
   `K_ATTRACT`.
2. **Repulsion**: for each of the 8 ray proximity sensors that currently
   detects something within `OBSTACLE_INFLUENCE` meters, a vector pointing
   *away* from that sensor's direction, magnitude growing sharply as the
   obstacle gets closer (inverse-square falloff), scaled by `K_REPEL`.
3. These vectors are summed into one desired heading. The robot turns
   toward it (`turn_rate = 2.0 * heading_error`) and moves forward at a
   speed that falls off as `cos(heading_error)` — i.e. it slows down/turns
   in place when it needs to turn sharply, and moves at full speed when
   already pointed the right way.
4. The new pose is applied directly to the robot object
   (`sim.setObjectPosition` / `sim.setObjectOrientation`) — see
   [Known limitations](#known-limitations) on why there's no wheel physics.

This is a **local, reactive** method: it has no map and does no lookahead
planning, so it can in principle get stuck in symmetric dead-ends (a
classic potential-field failure mode). It was sufficient for this scene's
layout and is easy to reason about/tune, which is what an MVP calls for.

## How delivery is detected

`controller.py` treats the parcel as delivered only when **both**:

- the robot's position is within `GOAL_ARRIVE_RADIUS` (0.45m) of the goal
  coordinate, **and**
- the onboard camera's current frame has a green-pixel ratio above
  `GREEN_PIXEL_RATIO_THRESHOLD` (0.03), computed via an HSV color
  threshold over the goal beacon's known green color.

This double-check is deliberate: it's meant to demonstrate the "vision"
half of "vision and sensors," not just have the robot stop when a
hardcoded coordinate is reached.

## Configuration knobs

All in `scripts/build_scene.py` and `scripts/controller.py` (no config
file — this is an MVP):

| Variable | File | What it does |
|---|---|---|
| `POINT_A`, `POINT_B` | `build_scene.py` | start / goal world coordinates |
| `WALL_SEGMENTS`, `OBSTACLES` | `build_scene.py` | scene layout |
| `SENSOR_COUNT`, `SENSOR_RANGE` | `build_scene.py` | proximity sensor ring density/range |
| `GOAL`, `GOAL_ARRIVE_RADIUS` | `controller.py` | must match `POINT_B` above |
| `MAX_SPEED`, `K_ATTRACT`, `K_REPEL`, `OBSTACLE_INFLUENCE` | `controller.py` | navigation tuning |
| `GREEN_PIXEL_RATIO_THRESHOLD` | `controller.py` | vision confirmation sensitivity |

## Known limitations

Intentionally out of scope for this MVP — noting them explicitly so
they're not mistaken for oversights:

- **No physics-based locomotion.** The robot body is a static shape moved
  kinematically each tick, not a dynamic body driven by wheel joints/motors.
  This was a deliberate simplification after the CoppeliaSim EDU bundled
  Pioneer p3dx robot model proved unreliable to load under this
  environment's software-rendering constraints (see git history / prior
  iteration for the model-based attempt). The navigation *logic* (sensors
  in, motion out) is the same either way; only the actuation layer differs.
- **No SLAM / mapping.** The goal coordinate is hardcoded, standing in for
  a localization system. A real "navigate any indoor environment" robot
  needs mapping (SLAM) and global path planning (A\*/RRT); this repo only
  demonstrates the local reactive layer.
- **Potential-field navigation can get stuck** in symmetric obstacle
  configurations (a well-known limitation of the technique). Not an issue
  for the current scene's layout.
- **No collision physics** on the robot (it's non-respondable) — obstacle
  avoidance is purely sensor/logic-driven, so a controller bug could in
  principle drive the robot through a wall. It doesn't, but nothing at the
  physics layer would stop it if it tried.
- **Single hardcoded scenario.** One floor plan, one A/B pair. Extending
  to arbitrary/random environments would need programmatic scene
  generation (easy extension of `build_scene.py`) and replacing the
  hardcoded goal with actual perception-based localization.

## Troubleshooting

**`docker exec ... python3 ...` hangs indefinitely.**
This was observed during development: CoppeliaSim's ZMQ remote API server
add-on is single-threaded and stateful per client UUID. If a previous
`docker exec` client is killed from the *host* side (e.g. by a `timeout`
wrapper), the process **inside** the container is often not killed with
it, and can be left holding an open, half-finished request that
destabilizes the server for new clients. If things stop responding:

```bash
docker exec mark2sim ps aux | grep python3   # find stale python processes
docker exec mark2sim kill -9 <pid>            # kill the stale one(s)
```

If that doesn't recover it, the cheapest fix is restarting the container:

```bash
./start_sim.sh
```

This is why `run_demo.py` deliberately does the scene build and the
control loop over a **single** connection instead of two separate
`docker exec` invocations — fewer client connections/reconnects means
fewer chances to hit this.

**Simulated time is much slower than real time.**
Expected — there's no GPU in the container, so CoppeliaSim renders (and
the vision sensor reads back frames) via software rendering (`llvmpipe`).
A ~30s simulated delivery run can take several real-world minutes.

**noVNC page loads but shows a black/blank screen.**
Give CoppeliaSim a few more seconds to finish starting before connecting
(`start_sim.sh` already waits 6s before starting the VNC bridge, which
resolved this in testing). If it persists, check `docker logs mark2sim`
for Qt/GL errors.

## License note

This repository's code (the Python scripts, Dockerfile, shell scripts) is
provided as-is. The Dockerfile downloads **CoppeliaSim EDU** at build time
directly from Coppelia Robotics — it is not redistributed in this repo.
CoppeliaSim EDU is free for private, non-commercial, and educational use;
review [Coppelia Robotics' license terms](https://www.coppeliarobotics.com/)
before any commercial use.
