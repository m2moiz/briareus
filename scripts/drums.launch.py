#!/usr/bin/env python3
"""Bring up the bimanual OpenArm (fake hardware) with two drumsticks rendered.

This mirrors openarm_bringup/openarm.bimanual.launch.py: it builds the robot
description from the same xacro, then injects two fixed drumstick links (one per
gripper, attached to *_ee_base_link) into the URDF so the sim actually renders the
sticks. The sticks are fixed links with no joints, so ros2_control is unaffected;
robot_state_publisher just publishes their geometry. A foxglove_bridge is included
so you can watch it on the Mac at ws://localhost:8765.

    ros2 launch drums.launch.py        # (scripts/drums.sh does this for you)
"""
import os
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import TimerAction
from launch_ros.actions import Node

# A drumstick: a thin wooden cylinder held in the gripper. The gripper fingers
# extend along -Z of ee_base_link (they sit at z=-0.068), so the stick emerges from
# the grasp point and points out along -Z, the way a held stick would.
STICK = """
  <link name="{side}_drumstick">
    <visual>
      <origin xyz="0 0 -0.17" rpy="0 0 0"/>
      <geometry><cylinder radius="0.0075" length="0.34"/></geometry>
      <material name="drumstick_{side}"><color rgba="0.80 0.62 0.40 1.0"/></material>
    </visual>
  </link>
  <joint name="{side}_drumstick_mount" type="fixed">
    <parent link="openarm_{side}_ee_base_link"/>
    <child link="{side}_drumstick"/>
    <origin xyz="0 0 -0.068" rpy="0 0 0"/>
  </joint>
"""


def robot_description_with_sticks():
    desc = get_package_share_directory("openarm_description")
    xacro_path = os.path.join(desc, "assets", "robot", "openarm_v2.0", "urdf",
                              "openarm_v20.urdf.xacro")
    urdf = xacro.process_file(xacro_path, mappings={
        "arm_type": "openarm_v2.0",
        "bimanual": "true",
        "use_fake_hardware": "true",
        "ros2_control": "true",
        "right_can_interface": "can0",
        "left_can_interface": "can1",
    }).toxml()
    sticks = STICK.format(side="left") + STICK.format(side="right")
    return urdf.replace("</robot>", sticks + "\n</robot>")


def generate_launch_description():
    rd = {"robot_description": robot_description_with_sticks()}
    controllers = os.path.join(
        get_package_share_directory("openarm_bringup"),
        "config", "controllers", "openarm_bimanual_controllers.yaml")

    def spawn(*names):
        return Node(package="controller_manager", executable="spawner",
                    arguments=[*names, "-c", "/controller_manager"], output="screen")

    return LaunchDescription([
        Node(package="robot_state_publisher", executable="robot_state_publisher",
             parameters=[rd], output="screen"),
        Node(package="controller_manager", executable="ros2_control_node",
             parameters=[rd, controllers], output="both"),
        Node(package="foxglove_bridge", executable="foxglove_bridge",
             parameters=[{"port": 8765, "address": "0.0.0.0"}], output="screen"),
        TimerAction(period=2.0, actions=[spawn("joint_state_broadcaster")]),
        TimerAction(period=3.0, actions=[
            spawn("left_joint_trajectory_controller", "right_joint_trajectory_controller")]),
        TimerAction(period=3.0, actions=[
            spawn("left_gripper_controller", "right_gripper_controller")]),
    ])
