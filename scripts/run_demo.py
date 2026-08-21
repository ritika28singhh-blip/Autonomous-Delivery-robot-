"""
MVP entry point: build the delivery scene and run the controller in one
process, using a single ZMQ Remote API connection for both steps.

    python3 run_demo.py [--max-time 60] [--video /workspace/videos/run.mp4]
"""
import argparse

from coppeliasim_zmqremoteapi_client import RemoteAPIClient

import build_scene
import controller


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-time", type=float, default=60.0)
    parser.add_argument("--video", default="/workspace/videos/delivery_run.mp4")
    parser.add_argument("--save-scene", default="/workspace/scenes/delivery_demo.ttt")
    args = parser.parse_args()

    client = RemoteAPIClient()
    build_scene.build(client, save_path=args.save_scene)

    sim = client.require('sim')
    robot, camera, sensors = controller.get_handles(sim)
    ok = controller.run_with_sim(sim, robot, camera, sensors, args.max_time, args.video)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
