#!/usr/bin/env python3
"""Wiggle the bimanual OpenArm so motion is visible live in Foxglove / RViz.

Publishes slow, phase-shifted sinusoidal JointTrajectory commands to both arm
controllers. Run INSIDE the VM after the bringup is up (use_fake_hardware:=true):

    ros2 launch openarm_bringup openarm.bimanual.launch.py use_fake_hardware:=true &
    python3 wiggle.py            # Ctrl-C to stop

Params (ROS):  amplitude (rad, default 0.3)  period (s, default 6.0)  rate (Hz, default 20)
"""
import math

import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

LEFT = [f"openarm_left_joint{i}" for i in range(1, 8)]
RIGHT = [f"openarm_right_joint{i}" for i in range(1, 8)]


class Wiggle(Node):
    def __init__(self) -> None:
        super().__init__("openarm_wiggle")
        self.amp = float(self.declare_parameter("amplitude", 0.3).value)
        self.period = float(self.declare_parameter("period", 6.0).value)
        self.rate = float(self.declare_parameter("rate", 20.0).value)
        self.left = self.create_publisher(
            JointTrajectory, "/left_joint_trajectory_controller/joint_trajectory", 10
        )
        self.right = self.create_publisher(
            JointTrajectory, "/right_joint_trajectory_controller/joint_trajectory", 10
        )
        self.points = 60  # waypoints per oscillation cycle
        # Send a full smooth cycle as one multi-point trajectory, re-published
        # just before it ends so the motion loops. (A single-point trajectory
        # re-sent at high rate just resets the controller and never moves.)
        self.create_timer(max(self.period - 0.3, 0.5), self._publish_cycle)
        self._publish_cycle()
        self.get_logger().info(
            f"wiggling both arms (amp={self.amp} rad, period={self.period}s) — Ctrl-C to stop"
        )

    def _cycle(self, names, phase: float) -> JointTrajectory:
        msg = JointTrajectory()
        msg.joint_names = names
        for k in range(1, self.points + 1):
            t = (k / self.points) * self.period
            pt = JointTrajectoryPoint()
            # phase-shift each joint a little so it reads as a travelling wave
            pt.positions = [
                self.amp * math.sin(2 * math.pi * t / self.period + phase + 0.4 * i)
                for i in range(len(names))
            ]
            pt.time_from_start = Duration(sec=int(t), nanosec=int((t % 1) * 1e9))
            msg.points.append(pt)
        return msg

    def _publish_cycle(self) -> None:
        self.left.publish(self._cycle(LEFT, 0.0))
        self.right.publish(self._cycle(RIGHT, math.pi))  # arms counter-phase


def main() -> None:
    rclpy.init()
    node = Wiggle()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
