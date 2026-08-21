"""
End-to-end delivery-robot controller (MVP).

Navigation = reactive potential field:
  - attractive pull toward the known goal coordinate (stands in for a
    localization/GPS fix a real indoor robot would get from SLAM)
  - repulsive push away from whatever the ring of ray proximity sensors
    reports nearby (the "sensors" half of the stack)
The robot is moved kinematically each tick (position/orientation set
directly from an integrated unicycle model) -- no wheel joints/dynamics,
which keeps this MVP simple and fast under software rendering.

Vision = the robot's camera watches for the green goal marker/beacon
(OpenCV color threshold) and only declares "delivered" once it can both
see the marker AND is within range of it, then stops.

Run inside the mark2-coppeliasim Docker image, against a scene already
built by build_scene.py, with CoppeliaSim's ZMQ remote API server running:

    python3 controller.py [--max-time 90] [--video /workspace/videos/run.mp4]
"""
import argparse
import math
import time

import cv2
import numpy as np
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

GOAL = (3.2, -3.3)
ROBOT_Z = 0.1
GOAL_ARRIVE_RADIUS = 0.45      # meters: close enough + marker visible = delivered
MAX_SPEED = 0.6                # m/s
K_ATTRACT = 1.0
K_REPEL = 0.5
OBSTACLE_INFLUENCE = 1.0       # meters: sensors beyond this range are ignored
SENSOR_COUNT = 8
GREEN_PIXEL_RATIO_THRESHOLD = 0.03
DT = 0.05


def sensor_angle(i):
    return 2 * math.pi * i / SENSOR_COUNT


def get_handles(sim):
    robot = sim.getObject("/DeliveryRobot")
    camera = sim.getObject("/DeliveryRobot/RobotCamera")
    sensors = [sim.getObject(f"/DeliveryRobot/proxSensor_{i}") for i in range(SENSOR_COUNT)]
    return robot, camera, sensors


def read_proximity_repulsion(sim, sensors, robot_yaw):
    fx, fy = 0.0, 0.0
    for i, h in enumerate(sensors):
        res = sim.readProximitySensor(h)
        detected, dist = res[0], res[1]
        if detected and 1e-4 < dist < OBSTACLE_INFLUENCE:
            ang = robot_yaw + sensor_angle(i)
            mag = K_REPEL * (1.0 / dist - 1.0 / OBSTACLE_INFLUENCE) / (dist ** 2)
            fx -= mag * math.cos(ang)
            fy -= mag * math.sin(ang)
    return fx, fy


def see_green_marker(sim, camera):
    img, res = sim.getVisionSensorImg(camera)
    resx, resy = res[0], res[1]
    frame = np.frombuffer(img, dtype=np.uint8).reshape(resy, resx, 3)
    frame = np.flipud(frame)  # CoppeliaSim images are bottom-up
    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
    lower = np.array([40, 60, 40])
    upper = np.array([85, 255, 255])
    mask = cv2.inRange(hsv, lower, upper)
    ratio = float(np.count_nonzero(mask)) / mask.size
    return ratio, frame


def run(max_time, video_path):
    client = RemoteAPIClient()
    sim = client.require('sim')
    robot, camera, sensors = get_handles(sim)
    return run_with_sim(sim, robot, camera, sensors, max_time, video_path)


def run_with_sim(sim, robot, camera, sensors, max_time, video_path):
    pos = sim.getObjectPosition(robot, -1)
    orient = sim.getObjectOrientation(robot, -1)
    x, y, yaw = pos[0], pos[1], orient[2]

    writer = None
    if video_path:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(video_path, fourcc, int(1 / DT), (256, 256))

    sim.startSimulation()
    start_wall = time.time()
    delivered = False

    try:
        while time.time() - start_wall < max_time:
            gx, gy = GOAL
            dx, dy = gx - x, gy - y
            dist_to_goal = math.hypot(dx, dy)

            green_ratio, frame = see_green_marker(sim, camera)
            if writer is not None:
                writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

            if dist_to_goal < GOAL_ARRIVE_RADIUS and green_ratio > GREEN_PIXEL_RATIO_THRESHOLD:
                delivered = True
                print(f"[t={time.time()-start_wall:5.1f}s] Parcel DELIVERED at B "
                      f"(dist={dist_to_goal:.2f}m, green_ratio={green_ratio:.3f})")
                break

            ax = K_ATTRACT * dx / max(dist_to_goal, 1e-3)
            ay = K_ATTRACT * dy / max(dist_to_goal, 1e-3)
            rx, ry = read_proximity_repulsion(sim, sensors, yaw)

            fx, fy = ax + rx, ay + ry
            desired_heading = math.atan2(fy, fx)
            heading_err = math.atan2(math.sin(desired_heading - yaw), math.cos(desired_heading - yaw))

            speed = max(0.0, math.cos(heading_err)) * MAX_SPEED
            turn_rate = 2.0 * heading_err

            yaw += turn_rate * DT
            x += speed * math.cos(yaw) * DT
            y += speed * math.sin(yaw) * DT

            sim.setObjectPosition(robot, -1, [x, y, ROBOT_Z])
            sim.setObjectOrientation(robot, -1, [0.0, 0.0, yaw])

            if int((time.time() - start_wall) * 2) % 2 == 0:
                print(f"[t={time.time()-start_wall:5.1f}s] pos=({x:.2f},{y:.2f}) "
                      f"dist_to_B={dist_to_goal:.2f}m green_ratio={green_ratio:.3f}")

            time.sleep(DT)
    finally:
        sim.stopSimulation()
        if writer is not None:
            writer.release()

    if not delivered:
        print("Delivery run ended WITHOUT reaching the goal within max_time.")
    return delivered


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-time", type=float, default=90.0)
    parser.add_argument("--video", default="/workspace/videos/delivery_run.mp4")
    args = parser.parse_args()

    ok = run(args.max_time, args.video)
    raise SystemExit(0 if ok else 1)
