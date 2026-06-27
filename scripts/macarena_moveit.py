#!/usr/bin/env python3
"""Macarena via MoveIt — the collision-aware version of macarena.py.

Same choreography, but every beat is PLANNED + EXECUTED by MoveIt (self-collision
checked against the body + both arms, velocity-scaled) instead of raw trajectory
publishing. A beat whose goal would self-collide is reported and skipped, not
driven blindly — so converting to MoveIt also reveals which hand-tuned poses were
actually unsafe.

Requires move_group running (`just moveit`). Run inside the VM.
"""
import rclpy
from moveit_motion import MoveItMotion

# right arm = left arm mirrored (negate all joints except the elbow, index 3)
MIRROR     = [-1, -1, -1, +1, -1, -1, -1]
HOME       = [0.0,  0.0, 0.0, 0.00, 0.0, 0.0, 0.0]
ARM_OUT    = [0.0, -1.4, 0.0, 0.15, 0.0, 0.0, 0.0]
PALM_UP    = [0.0, -1.4, 0.0, 0.15, 1.3, 0.0, 0.0]
CROSS      = [0.9, -1.6, 0.0, 1.90, 0.0, 0.0, 0.0]
HANDS_HEAD = [0.0, -2.9, 0.0, 1.70, 0.0, 0.0, 0.0]
HANDS_HIP  = [-0.4, -0.3, 0.0, 1.30, 0.0, 0.0, 0.0]


def mirror(p):
    return [s * v for s, v in zip(MIRROR, p)]


def main():
    rclpy.init()
    m = MoveItMotion(vel_scale=0.2)        # MoveIt's own velocity scaling
    ok = fail = 0

    def beat(group, pose, label):
        nonlocal ok, fail
        m.get_logger().info(f"--- {label} ---")
        target = mirror(pose) if group == "right_arm" else pose
        if m.go_to_joints(group, target):
            ok += 1
        else:
            fail += 1

    try:
        beat("right_arm", HOME, "home R"); beat("left_arm", HOME, "home L")
        beat("right_arm", ARM_OUT, "R arm out");    beat("left_arm", ARM_OUT, "L arm out")
        beat("right_arm", PALM_UP, "R palm up");     beat("left_arm", PALM_UP, "L palm up")
        beat("right_arm", CROSS, "R cross");         beat("left_arm", CROSS, "L cross")
        beat("right_arm", HANDS_HEAD, "R to head");  beat("left_arm", HANDS_HEAD, "L to head")
        beat("right_arm", HANDS_HIP, "R to hip");    beat("left_arm", HANDS_HIP, "L to hip")
        beat("right_arm", HOME, "home R"); beat("left_arm", HOME, "home L")
        m.get_logger().info(
            f"Macarena via MoveIt complete — {ok} beats executed, "
            f"{fail} skipped (collision/unreachable, blocked by MoveIt)")
    finally:
        m.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
