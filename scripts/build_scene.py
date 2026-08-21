"""
Builds the delivery-robot demo scene entirely from the CoppeliaSim
ZeroMQ Remote API (no manual scene editing, no external model files).

Layout: a simple indoor floor plan with two rooms connected by a doorway,
a scatter of static box "furniture" obstacles, a robot at point A, and a
green floor marker + beacon at point B that the robot's vision sensor is
meant to detect and stop at ("deliver the parcel").

The robot itself is a plain static shape moved kinematically by the
controller (no wheel joints/dynamics) -- simplest thing that lets a camera
+ proximity-sensor ring actually navigate, which is all this MVP needs.

Run inside the mark2-coppeliasim Docker image, with CoppeliaSim already
listening on the ZMQ remote API port (default 23000):

    python3 build_scene.py [--save /workspace/scenes/delivery_demo.ttt]
"""
import argparse
import math

from coppeliasim_zmqremoteapi_client import RemoteAPIClient

WALL_HEIGHT = 0.5
WALL_THICK = 0.05
FLOOR_SIZE = 8.0
SENSOR_COUNT = 8
SENSOR_RANGE = 1.0

# Room walls as (x, y, length, angle_deg) segments, in meters, forming two
# rooms joined by a doorway gap so the robot has to navigate a corridor.
WALL_SEGMENTS = [
    (0.0, -4.0, 8.0, 0.0),    # south outer wall
    (0.0, 4.0, 8.0, 0.0),     # north outer wall
    (-4.0, 0.0, 8.0, 90.0),   # west outer wall
    (4.0, 0.0, 8.0, 90.0),    # east outer wall
    (0.0, 1.5, 3.0, 90.0),    # middle divider, upper part (leaves a doorway gap)
    (0.0, -2.5, 3.0, 90.0),   # middle divider, lower part
]

# Static box obstacles scattered around both rooms: (x, y, size_x, size_y, size_z)
OBSTACLES = [
    (-2.3, 2.6, 0.6, 0.6, 0.6),
    (-1.0, 2.8, 0.4, 1.2, 0.5),
    (2.0, 3.0, 0.8, 0.4, 0.4),
    (-2.5, -1.5, 0.5, 0.5, 0.6),
    (-3.0, -3.0, 0.6, 1.0, 0.5),
    (1.5, -1.0, 0.4, 0.4, 0.5),
    (2.6, -2.8, 0.7, 0.7, 0.5),
]

POINT_A = (-3.3, 3.3, 0.0)   # robot start
POINT_B = (3.2, -3.3, 0.0)   # delivery target (green marker)
ROBOT_Z = 0.1


def add_floor(sim):
    handle = sim.createPrimitiveShape(sim.primitiveshape_cuboid, [FLOOR_SIZE, FLOOR_SIZE, 0.02], 0)
    sim.setObjectPosition(handle, -1, [0, 0, -0.01])
    sim.setObjectAlias(handle, "Floor")
    sim.setObjectInt32Param(handle, sim.shapeintparam_static, 1)
    sim.setObjectInt32Param(handle, sim.shapeintparam_respondable, 1)
    sim.setShapeColor(handle, None, sim.colorcomponent_ambient_diffuse, [0.75, 0.75, 0.75])
    return handle


def add_wall(sim, idx, x, y, length, angle_deg):
    handle = sim.createPrimitiveShape(sim.primitiveshape_cuboid, [length, WALL_THICK, WALL_HEIGHT], 0)
    sim.setObjectPosition(handle, -1, [x, y, WALL_HEIGHT / 2])
    sim.setObjectOrientation(handle, -1, [0, 0, math.radians(angle_deg)])
    sim.setObjectAlias(handle, f"Wall_{idx}")
    sim.setObjectInt32Param(handle, sim.shapeintparam_static, 1)
    sim.setObjectInt32Param(handle, sim.shapeintparam_respondable, 1)
    sim.setShapeColor(handle, None, sim.colorcomponent_ambient_diffuse, [0.85, 0.8, 0.7])
    return handle


def add_obstacle(sim, idx, x, y, sx, sy, sz):
    handle = sim.createPrimitiveShape(sim.primitiveshape_cuboid, [sx, sy, sz], 0)
    sim.setObjectPosition(handle, -1, [x, y, sz / 2])
    sim.setObjectAlias(handle, f"Obstacle_{idx}")
    sim.setObjectInt32Param(handle, sim.shapeintparam_static, 1)
    sim.setObjectInt32Param(handle, sim.shapeintparam_respondable, 1)
    sim.setShapeColor(handle, None, sim.colorcomponent_ambient_diffuse, [0.55, 0.35, 0.2])
    return handle


def add_goal_marker(sim, x, y):
    # Flat green disc on the floor plus a green vertical beacon so the
    # robot's camera can pick up delivery point B from a distance.
    disc = sim.createPrimitiveShape(sim.primitiveshape_disc, [0.7, 0.7, 0.01], 0)
    sim.setObjectPosition(disc, -1, [x, y, 0.005])
    sim.setObjectAlias(disc, "GoalMarker_B")
    sim.setObjectInt32Param(disc, sim.shapeintparam_static, 1)
    sim.setObjectInt32Param(disc, sim.shapeintparam_respondable, 0)
    sim.setShapeColor(disc, None, sim.colorcomponent_ambient_diffuse, [0.1, 0.9, 0.1])

    beacon = sim.createPrimitiveShape(sim.primitiveshape_cylinder, [0.15, 0.15, 0.6], 0)
    sim.setObjectPosition(beacon, -1, [x, y, 0.3])
    sim.setObjectAlias(beacon, "GoalBeacon_B")
    sim.setObjectInt32Param(beacon, sim.shapeintparam_static, 1)
    sim.setObjectInt32Param(beacon, sim.shapeintparam_respondable, 0)
    sim.setShapeColor(beacon, None, sim.colorcomponent_ambient_diffuse, [0.1, 0.9, 0.1])
    return disc, beacon


def add_start_marker(sim, x, y):
    disc = sim.createPrimitiveShape(sim.primitiveshape_disc, [0.5, 0.5, 0.01], 0)
    sim.setObjectPosition(disc, -1, [x, y, 0.004])
    sim.setObjectAlias(disc, "StartMarker_A")
    sim.setObjectInt32Param(disc, sim.shapeintparam_static, 1)
    sim.setObjectInt32Param(disc, sim.shapeintparam_respondable, 0)
    sim.setShapeColor(disc, None, sim.colorcomponent_ambient_diffuse, [0.9, 0.7, 0.1])
    return disc


def add_robot(sim, x, y):
    """A plain box body moved kinematically by the controller (no wheel
    joints/dynamics -- this is a navigation-stack demo, not a wheel-physics
    demo), with a camera and a ring of ray proximity sensors attached."""
    body = sim.createPrimitiveShape(sim.primitiveshape_cuboid, [0.35, 0.25, 0.15], 0)
    sim.setObjectPosition(body, -1, [x, y, ROBOT_Z])
    sim.setObjectAlias(body, "DeliveryRobot")
    sim.setObjectInt32Param(body, sim.shapeintparam_static, 1)
    sim.setObjectInt32Param(body, sim.shapeintparam_respondable, 0)
    sim.setShapeColor(body, None, sim.colorcomponent_ambient_diffuse, [0.2, 0.4, 0.9])

    vision = sim.createVisionSensor(
        2,  # perspective mode
        [256, 256, 0, 0],
        [0.02, 5.0, 60 * math.pi / 180, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    )
    sim.setObjectAlias(vision, "RobotCamera")
    sim.setObjectParent(vision, body, True)
    sim.setObjectPosition(vision, body, [0.0, 0.0, 0.12])
    sim.setObjectOrientation(vision, body, [math.pi / 2, 0, math.pi / 2])

    sensors = []
    for i in range(SENSOR_COUNT):
        ang = 2 * math.pi * i / SENSOR_COUNT
        s = sim.createProximitySensor(
            sim.proximitysensor_ray_subtype,
            16,
            4,  # options: detection volume not shown
            [0, 0, 0, 0, 0, 0, 0, 0],
            [0.0, SENSOR_RANGE, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        )
        sim.setObjectAlias(s, f"proxSensor_{i}")
        sim.setObjectParent(s, body, True)
        sim.setObjectPosition(s, body, [0.0, 0.0, 0.0])
        sim.setObjectOrientation(s, body, [0.0, math.pi / 2, ang])
        sensors.append(s)

    return body, vision, sensors


def build(client, save_path=None):
    sim = client.require('sim')
    sim.stopSimulation()
    while sim.getSimulationState() != sim.simulation_stopped:
        pass

    sim.closeScene()
    add_floor(sim)
    for i, seg in enumerate(WALL_SEGMENTS):
        add_wall(sim, i, *seg)
    for i, obs in enumerate(OBSTACLES):
        add_obstacle(sim, i, *obs)
    add_start_marker(sim, POINT_A[0], POINT_A[1])
    add_goal_marker(sim, POINT_B[0], POINT_B[1])
    robot, vision, sensors = add_robot(sim, POINT_A[0], POINT_A[1])

    if save_path:
        sim.saveScene(save_path)
        print(f"Scene saved to {save_path}")

    print(f"Scene built. Robot handle={robot}, camera handle={vision}, sensors={len(sensors)}")
    print(f"Point A (start) = {POINT_A}, Point B (goal) = {POINT_B}")
    return robot, vision, sensors


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", default="/workspace/scenes/delivery_demo.ttt")
    args = parser.parse_args()

    client = RemoteAPIClient()
    build(client, save_path=args.save)
