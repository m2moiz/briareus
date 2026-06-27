#!/usr/bin/env python3
"""Scripted bimanual motion for the OpenArm sim — a starting point for app logic.

Commands the two arm trajectory controllers directly (the same interface MoveIt
executes through), so it runs against the fake-hardware sim AND, unchanged, the
real arm. Named poses (home, hands_up, …) are read from the MoveIt SRDF, so
adding a <group_state> there makes it available here with no code change.

This is the controller-level path: joint-space goals, no collision-aware
planning. For IK / collision-aware planning to arbitrary Cartesian poses, drive
the running move_group via its /move_action goal instead (see README).

Run inside the VM with the sim already up (`just moveit` or `just demo`):
    python3 bimanual_sequence.py            # home -> hands_up -> wave -> home
    python3 bimanual_sequence.py hands_up   # just strike one named pose and hold
"""
import math
import sys
import xml.etree.ElementTree as ET

import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

LEFT_JOINTS = [f"openarm_left_joint{i}" for i in range(1, 8)]
RIGHT_JOINTS = [f"openarm_right_joint{i}" for i in range(1, 8)]
LEFT_TOPIC = "/left_joint_trajectory_controller/joint_trajectory"
RIGHT_TOPIC = "/right_joint_trajectory_controller/joint_trajectory"


def _dur(seconds: float) -> Duration:
    return Duration(sec=int(seconds), nanosec=int((seconds % 1.0) * 1e9))


class BimanualSequencer(Node):
    def __init__(self):
        super().__init__("bimanual_sequencer")
        self.left_pub = self.create_publisher(JointTrajectory, LEFT_TOPIC, 10)
        self.right_pub = self.create_publisher(JointTrajectory, RIGHT_TOPIC, 10)
        self.poses = self._load_named_poses()  # {pose_name: {joint: value}}
        self.get_logger().info(f"named poses from SRDF: {sorted(self.poses)}")
        # let publisher↔controller discovery settle before the first send
        self._spin(1.0)

    # --- read <group_state> targets straight out of the MoveIt SRDF ---
    def _load_named_poses(self):
        share = get_package_share_directory("openarm_bimanual_moveit_config")
        srdf = f"{share}/config/openarm_v2.0/openarm_bimanual.srdf"
        poses: dict[str, dict[str, float]] = {}
        for gs in ET.parse(srdf).getroot().findall("group_state"):
            name = gs.get("name")
            joints = poses.setdefault(name, {})
            for j in gs.findall("joint"):
                joints[j.get("name")] = float(j.get("value"))
        return poses

    def _positions(self, joint_names, pose_name):
        pose = self.poses[pose_name]
        return [pose.get(j, 0.0) for j in joint_names]

    def _spin(self, seconds: float):
        end = self.get_clock().now().nanoseconds + int(seconds * 1e9)
        while self.get_clock().now().nanoseconds < end:
            rclpy.spin_once(self, timeout_sec=0.05)

    # --- low-level: send one waypoint per arm and wait for it to play out ---
    def goto(self, left_pos, right_pos, seconds=2.5, settle=0.4):
        for pub, joints, pos in (
            (self.left_pub, LEFT_JOINTS, left_pos),
            (self.right_pub, RIGHT_JOINTS, right_pos),
        ):
            traj = JointTrajectory(joint_names=joints)
            traj.points = [JointTrajectoryPoint(positions=pos, time_from_start=_dur(seconds))]
            pub.publish(traj)
        self._spin(seconds + settle)

    def goto_named(self, pose_name, seconds=2.5):
        self.get_logger().info(f"→ {pose_name}")
        self.goto(self._positions(LEFT_JOINTS, pose_name),
                  self._positions(RIGHT_JOINTS, pose_name), seconds)

    # --- a wave: oscillate each wrist (joint6) around the hands_up pose ---
    def wave(self, cycles=3, amplitude=0.6, period=1.2):
        self.get_logger().info("→ wave")
        base_l = self._positions(LEFT_JOINTS, "hands_up")
        base_r = self._positions(RIGHT_JOINTS, "hands_up")
        wrist = 5  # joint6 (0-indexed)
        steps_per_cycle = 12
        lt = JointTrajectory(joint_names=LEFT_JOINTS)
        rt = JointTrajectory(joint_names=RIGHT_JOINTS)
        for n in range(cycles * steps_per_cycle + 1):
            t = n * period / steps_per_cycle
            offset = amplitude * math.sin(2 * math.pi * t / period)
            l, r = list(base_l), list(base_r)
            l[wrist] = base_l[wrist] + offset
            r[wrist] = base_r[wrist] - offset  # mirror so it looks like a wave
            lt.points.append(JointTrajectoryPoint(positions=l, time_from_start=_dur(t)))
            rt.points.append(JointTrajectoryPoint(positions=r, time_from_start=_dur(t)))
        self.left_pub.publish(lt)
        self.right_pub.publish(rt)
        self._spin(cycles * period + 0.5)

    def run_demo(self):
        self.goto_named("home", seconds=2.0)
        self.goto_named("hands_up", seconds=2.5)
        self._spin(1.0)
        self.wave(cycles=3)
        self.goto_named("home", seconds=2.5)
        self.get_logger().info("sequence complete")


def main():
    rclpy.init()
    seq = BimanualSequencer()
    try:
        if len(sys.argv) > 1:          # strike one named pose and hold
            seq.goto_named(sys.argv[1], seconds=2.5)
        else:                          # full choreography
            seq.run_demo()
    finally:
        seq.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
