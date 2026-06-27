#!/usr/bin/env python3
"""¡Macarena! — a bimanual dance for the OpenArm sim.

The classic 16-count routine is right-then-left arm moves, then a hip wiggle and
a quarter turn. A torso-mounted arm has no head / hips / legs, so each human move
is mapped to an expressive joint pose that *evokes* it (see the table in README).
The right arm is the left arm mirrored: every joint negated EXCEPT the elbow
(joint4), which shares the same axis on both sides.

Drives the trajectory controllers directly (same interface MoveIt executes
through), so it runs on the fake-hardware sim and, unchanged, the real arm.
Poses are joint-space and tuned for expressiveness — tweak the POSE constants to
restyle a move; they're all within the URDF joint limits.

Run inside the VM with the sim up (`just moveit` or `just demo`):
    python3 macarena.py
"""
import math
import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

LEFT_JOINTS = [f"openarm_left_joint{i}" for i in range(1, 8)]
RIGHT_JOINTS = [f"openarm_right_joint{i}" for i in range(1, 8)]
LEFT_TOPIC = "/left_joint_trajectory_controller/joint_trajectory"
RIGHT_TOPIC = "/right_joint_trajectory_controller/joint_trajectory"

# Mirror a LEFT-arm pose onto the RIGHT arm: negate every joint except the elbow
# (joint4, index 3), which has the same axis + range on both sides.
MIRROR = [-1, -1, -1, +1, -1, -1, -1]

# --- LEFT-arm key poses [j1..j7], all within limits; right side is mirrored ---
HOME      = [0.0,  0.0, 0.0, 0.00, 0.0, 0.0, 0.0]
ARM_OUT   = [0.0, -1.4, 0.0, 0.15, 0.0, 0.0, 0.0]   # extend forward, palm down
PALM_UP   = [0.0, -1.4, 0.0, 0.15, 1.3, 0.0, 0.0]   # ...then roll palm up
CROSS     = [0.9, -1.6, 0.0, 1.90, 0.0, 0.0, 0.0]   # forearm across the chest
HANDS_HEAD= [0.0, -2.9, 0.0, 1.70, 0.0, 0.0, 0.0]   # both hands up behind head
HANDS_HIP = [-0.4, -0.3, 0.0, 1.30, 0.0, 0.0, 0.0]  # elbows tucked to the waist


def mirror(pose):
    return [s * v for s, v in zip(MIRROR, pose)]


def _dur(seconds):
    return Duration(sec=int(seconds), nanosec=int((seconds % 1.0) * 1e9))


class Macarena(Node):
    def __init__(self):
        super().__init__("macarena")
        self.lpub = self.create_publisher(JointTrajectory, LEFT_TOPIC, 10)
        self.rpub = self.create_publisher(JointTrajectory, RIGHT_TOPIC, 10)
        self.l = list(HOME)   # current commanded targets
        self.r = list(HOME)
        self._spin(1.0)       # let pub↔controller discovery settle

    def _spin(self, seconds):
        end = self.get_clock().now().nanoseconds + int(seconds * 1e9)
        while self.get_clock().now().nanoseconds < end:
            rclpy.spin_once(self, timeout_sec=0.05)

    def _send(self, pub, joints, points):
        traj = JointTrajectory(joint_names=joints)
        traj.points = points
        pub.publish(traj)

    # move both arms to their current self.l / self.r targets over `seconds`
    def beat(self, seconds=0.9, hold=0.5):
        self._send(self.lpub, LEFT_JOINTS,
                   [JointTrajectoryPoint(positions=list(self.l), time_from_start=_dur(seconds))])
        self._send(self.rpub, RIGHT_JOINTS,
                   [JointTrajectoryPoint(positions=list(self.r), time_from_start=_dur(seconds))])
        self._spin(seconds + hold)

    def left(self, pose, **kw):        # move only the left arm
        self.l = list(pose); self.beat(**kw)

    def right(self, pose, **kw):       # move only the right arm (auto-mirrored)
        self.r = mirror(pose); self.beat(**kw)

    def both(self, pose, **kw):
        self.l = list(pose); self.r = mirror(pose); self.beat(**kw)

    # --- side-to-side sway: oscillate j1 on both arms, same world direction ---
    def wiggle(self, cycles=4, amplitude=0.6, period=0.9):
        steps = 10
        lpts, rpts = [], []
        for n in range(cycles * steps + 1):
            t = n * period / steps
            off = amplitude * math.sin(2 * math.pi * t / period)
            l = list(self.l); l[0] = self.l[0] + off
            r = list(self.r); r[0] = self.r[0] - off   # mirror -> same world sway
            lpts.append(JointTrajectoryPoint(positions=l, time_from_start=_dur(t)))
            rpts.append(JointTrajectoryPoint(positions=r, time_from_start=_dur(t)))
        self._send(self.lpub, LEFT_JOINTS, lpts)
        self._send(self.rpub, RIGHT_JOINTS, rpts)
        self._spin(cycles * period + 0.4)

    def dance(self):
        log = self.get_logger().info
        log("¡Dale a tu cuerpo alegría, Macarena!")
        self.both(HOME, seconds=1.2)
        # counts 1-2: arms out, palm down (right, then left)
        log("arms out");      self.right(ARM_OUT); self.left(ARM_OUT)
        # counts 3-4: palms up
        log("palms up");      self.right(PALM_UP); self.left(PALM_UP)
        # counts 5-6: cross to opposite shoulder
        log("cross");         self.right(CROSS);   self.left(CROSS)
        # counts 7-8: hands behind head
        log("hands to head"); self.right(HANDS_HEAD); self.left(HANDS_HEAD)
        # counts 9-10: hands on hips
        log("hands to hips"); self.right(HANDS_HIP); self.left(HANDS_HIP)
        # counts 11-14: ¡heeey! hip wiggle
        log("wiggle");        self.wiggle(cycles=4)
        # counts 15-16: quarter turn + snap home
        log("turn!");         self.both([1.0, -1.0, 0.0, 0.3, 0.0, 0.0, 0.0], seconds=0.7, hold=0.4)
        self.both(HOME, seconds=1.0)
        log("¡Macarena! 🕺")


def main():
    rclpy.init()
    node = Macarena()
    try:
        node.dance()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
