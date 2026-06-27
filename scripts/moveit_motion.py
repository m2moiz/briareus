#!/usr/bin/env python3
"""Collision-aware motion via MoveIt's MoveGroup action (no moveit_py needed).

Sends joint-space / named-pose goals to the running move_group (`/move_action`).
MoveIt plans each move against the robot's collision model (URDF geometry + the
SRDF allowed-collision matrix) and executes it through the controllers — so every
motion is self-collision-checked and velocity-scaled. This is the safe, standard
path; it replaces raw trajectory publishing.

A goal that is itself in collision (or unreachable) is REPORTED as a failure
rather than driven blindly — that's the whole point.

Requires move_group running (e.g. `just moveit` / demo.launch.py).
"""
import xml.etree.ElementTree as ET

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from ament_index_python.packages import get_package_share_directory
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (MotionPlanRequest, Constraints, JointConstraint,
                             PlanningOptions, MoveItErrorCodes)

# decode MoveIt error codes honestly (-4 CONTROL_FAILED is an EXECUTION failure,
# NOT a collision; -10/-12 are the collision ones)
ERR = {-1: "PLANNING_FAILED", -2: "INVALID_MOTION_PLAN", -4: "CONTROL_FAILED",
       -6: "TIMED_OUT", -7: "PREEMPTED", -10: "START_STATE_IN_COLLISION",
       -12: "GOAL_IN_COLLISION", -14: "GOAL_CONSTRAINTS_VIOLATED",
       -15: "INVALID_GROUP_NAME"}

LEFT_JOINTS = [f"openarm_left_joint{i}" for i in range(1, 8)]
RIGHT_JOINTS = [f"openarm_right_joint{i}" for i in range(1, 8)]
GROUP_JOINTS = {"left_arm": LEFT_JOINTS, "right_arm": RIGHT_JOINTS}


class MoveItMotion(Node):
    def __init__(self, vel_scale=0.2):
        super().__init__("moveit_motion")
        self.vel = float(vel_scale)
        self.client = ActionClient(self, MoveGroup, "/move_action")
        self.poses = self._load_named_poses()
        self.get_logger().info("waiting for move_group (/move_action)…")
        self.client.wait_for_server()

    # named SRDF poses keyed by (name, group), e.g. ("hands_up","left_arm")
    def _load_named_poses(self):
        share = get_package_share_directory("openarm_bimanual_moveit_config")
        srdf = f"{share}/config/openarm_v2.0/openarm_bimanual.srdf"
        poses = {}
        for gs in ET.parse(srdf).getroot().findall("group_state"):
            poses[(gs.get("name"), gs.get("group"))] = {
                j.get("name"): float(j.get("value")) for j in gs.findall("joint")}
        return poses

    def _goal(self, group, joints, positions):
        req = MotionPlanRequest()
        req.group_name = group
        req.num_planning_attempts = 10
        req.allowed_planning_time = 5.0
        req.max_velocity_scaling_factor = self.vel
        req.max_acceleration_scaling_factor = self.vel
        con = Constraints()
        for n, p in zip(joints, positions):
            jc = JointConstraint()
            jc.joint_name = n
            jc.position = float(p)
            jc.tolerance_above = 0.01
            jc.tolerance_below = 0.01
            jc.weight = 1.0
            con.joint_constraints.append(jc)
        req.goal_constraints.append(con)
        g = MoveGroup.Goal()
        g.request = req
        g.planning_options = PlanningOptions()
        g.planning_options.plan_only = False          # plan AND execute
        g.planning_options.planning_scene_diff.is_diff = True
        g.planning_options.planning_scene_diff.robot_state.is_diff = True
        return g

    def go_to_joints(self, group, positions):
        """Plan+execute a joint-space goal. Returns True on success."""
        sf = self.client.send_goal_async(self._goal(group, GROUP_JOINTS[group], positions))
        rclpy.spin_until_future_complete(self, sf)
        gh = sf.result()
        if gh is None or not gh.accepted:
            self.get_logger().warn(f"{group}: goal rejected")
            return False
        rf = gh.get_result_async()
        rclpy.spin_until_future_complete(self, rf)
        code = rf.result().result.error_code.val
        if code != MoveItErrorCodes.SUCCESS:
            self.get_logger().warn(f"{group}: failed ({code} {ERR.get(code, '?')})")
            return False
        return True

    def go_to_named(self, group, pose_name):
        key = (pose_name, group)
        if key not in self.poses:
            self.get_logger().error(f"no named pose {key}")
            return False
        joints = GROUP_JOINTS[group]
        self.get_logger().info(f"{group} -> {pose_name}")
        return self.go_to_joints(group, [self.poses[key].get(j, 0.0) for j in joints])
