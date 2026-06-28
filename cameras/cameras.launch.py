"""Bring up the three OpenArm UVC cameras with stable names + calibration.

Each camera publishes <ns>/image_raw and <ns>/camera_info. The camera_info_url
points at cameras/calib/<name>.yaml — written by the intrinsic calibration step;
until it exists, v4l2_camera just warns and streams uncalibrated.

    ros2 launch cameras/cameras.launch.py        # needs the udev names /dev/cam_*
"""
import os
from launch import LaunchDescription
from launch_ros.actions import Node

HERE = os.path.dirname(os.path.abspath(__file__))

# (node/ns name, udev device, tf frame, [width, height])
CAMERAS = [
    ("torso_camera",        "/dev/cam_torso",      "torso_camera_optical_frame",        [1280, 800]),
    ("left_gripper_camera", "/dev/cam_grip_left",  "left_gripper_camera_optical_frame", [1280, 800]),
    ("right_gripper_camera","/dev/cam_grip_right", "right_gripper_camera_optical_frame",[1280, 800]),
]


def generate_launch_description():
    nodes = []
    for name, dev, frame, size in CAMERAS:
        nodes.append(Node(
            package="v4l2_camera", executable="v4l2_camera_node", name=name, namespace=name,
            parameters=[{
                "video_device": dev,
                "camera_frame_id": frame,
                "image_size": size,
                "camera_info_url": f"file://{HERE}/calib/{name}.yaml",
            }],
            output="screen",
        ))
    return LaunchDescription(nodes)
