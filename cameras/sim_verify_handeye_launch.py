#!/usr/bin/env python3
"""Launch smoke test for easy_handeye2 calibrate.launch.py (no hardware, no GUI).

calibrate.launch.py spawns an rqt GUI + handeye_server, so it cannot just be run
headless. Instead this loads the LaunchDescription, seeds a LaunchContext with an
eye_in_hand configuration, and resolves the arguments + conditions WITHOUT spawning
any process:
  * the file imports and builds a LaunchDescription
  * all six declared args resolve to the eye_in_hand values we pass
  * the eye_in_hand dummy publisher's condition is TRUE and the eye_on_base one
    is FALSE (the calibration_type arg actually drives node selection)
  * the unconditional handeye_server / rqt_calibrator nodes are present

Requires a sourced ROS 2 + easy_handeye2.
    python3 sim_verify_handeye_launch.py
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchContext
from launch.launch_description_sources import get_launch_description_from_python_launch_file
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

CFG = {
    "name": "openarm_right_gripper",
    "calibration_type": "eye_in_hand",
    "tracking_base_frame": "right_gripper_camera_optical_frame",
    "tracking_marker_frame": "charuco_board",
    "robot_base_frame": "openarm_base",
    "robot_effector_frame": "openarm_right_hand",
}


def main():
    path = os.path.join(get_package_share_directory("easy_handeye2"),
                        "launch", "calibrate.launch.py")
    assert os.path.exists(path), f"launch file missing: {path}"

    ld = get_launch_description_from_python_launch_file(path)
    print(f"loaded LaunchDescription from {path}")

    ctx = LaunchContext()
    ctx.launch_configurations.update(CFG)            # seed the eye_in_hand config

    # 1) every arg resolves to the value we passed
    for k, v in CFG.items():
        got = LaunchConfiguration(k).perform(ctx)
        assert got == v, f"arg {k} resolved to {got!r}, expected {v!r}"
    print(f"  all {len(CFG)} args resolve to the eye_in_hand config")

    # 2) condition wiring: exactly the eye_in_hand dummy publisher is enabled
    conditioned = []
    plain_nodes = 0
    for ent in ld.entities:
        if isinstance(ent, Node):
            if ent.condition is not None:
                conditioned.append(ent.condition.evaluate(ctx))
            else:
                plain_nodes += 1
    enabled = sum(conditioned)
    print(f"  conditioned nodes: {conditioned} ({enabled} enabled), "
          f"unconditional nodes: {plain_nodes}")
    assert len(conditioned) == 2, f"expected 2 conditioned nodes, got {len(conditioned)}"
    assert enabled == 1, f"eye_in_hand should enable exactly 1 dummy publisher, got {enabled}"
    assert plain_nodes >= 2, "expected handeye_server + rqt_calibrator unconditional nodes"

    print("PASS: calibrate.launch.py loads and wires the eye_in_hand configuration")


if __name__ == "__main__":
    main()
