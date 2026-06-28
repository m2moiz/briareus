#!/usr/bin/env python3
"""Beat-synced Macarena — the dance timed to the song's 103 BPM grid.

Each move ARRIVES on its beat. Built as one timed trajectory per arm (waypoints
stamped at exact beat times) and handed to the trajectory controller, which
replays on precise timestamps — deterministic, so it lands on the beat. (Live
MoveIt planning is too slow/jittery to hit 0.58s beats; these poses are already
MoveIt-collision-validated, so we play them back timed.)

Canonical 16-count Macarena: right-then-left arm moves on beats 1-10, hip wiggle
11-15, reset on 16. A 4-beat count-in matches the click track so you can start
both together.

Run inside the VM with the controllers up (e.g. after `just moveit-dance`):
    python3 macarena_synced.py [BPM]    # default 103
"""
import sys
import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

LEFT_JOINTS = [f"openarm_left_joint{i}" for i in range(1, 8)]
RIGHT_JOINTS = [f"openarm_right_joint{i}" for i in range(1, 8)]
LTOPIC = "/left_joint_trajectory_controller/joint_trajectory"
RTOPIC = "/right_joint_trajectory_controller/joint_trajectory"

MIRROR     = [-1, -1, -1, +1, -1, -1, -1]      # right = left mirrored, except elbow
HOME       = [0.0,  0.0, 0.0, 0.00, 0.0, 0.0, 0.0]
ARM_OUT    = [0.0, -1.4, 0.0, 0.15, 0.0, 0.0, 0.0]
PALM_UP    = [0.0, -1.4, 0.0, 0.15, 1.3, 0.0, 0.0]
CROSS      = [0.9, -1.6, 0.0, 1.90, 0.0, 0.0, 0.0]
HANDS_HEAD = [0.0, -2.9, 0.0, 1.70, 0.0, 0.0, 0.0]
HANDS_HIP  = [-0.4, -0.3, 0.0, 1.30, 0.0, 0.0, 0.0]
SWAY_L     = [0.5,  0.0, 0.0, 0.00, 0.0, 0.0, 0.0]   # j1 sway for the hip wiggle
SWAY_R     = [-0.5, 0.0, 0.0, 0.00, 0.0, 0.0, 0.0]

COUNT_IN = 4          # beats of count-in (matches the click track)
MOVE_FRAC = 0.6       # fraction of a beat spent moving; the rest holds the pose

def mirror(p): return [s * v for s, v in zip(MIRROR, p)]

# (dance-beat, pose) keyframes — pose reached AT that beat
RIGHT_KEYS = [(1, ARM_OUT), (3, PALM_UP), (5, CROSS), (7, HANDS_HEAD), (9, HANDS_HIP),
              (11, HOME), (12, SWAY_L), (13, SWAY_R), (14, SWAY_L), (15, SWAY_R), (16, HOME)]
LEFT_KEYS  = [(2, ARM_OUT), (4, PALM_UP), (6, CROSS), (8, HANDS_HEAD), (10, HANDS_HIP),
              (11, HOME), (12, SWAY_L), (13, SWAY_R), (14, SWAY_L), (15, SWAY_R), (16, HOME)]


def _dur(t):
    return Duration(sec=int(t), nanosec=int((t % 1.0) * 1e9))


class Synced(Node):
    def __init__(self, bpm=103.0):
        super().__init__("macarena_synced")
        self.beat = 60.0 / bpm
        self.lpub = self.create_publisher(JointTrajectory, LTOPIC, 10)
        self.rpub = self.create_publisher(JointTrajectory, RTOPIC, 10)
        self._spin(1.0)

    def _spin(self, s):
        end = self.get_clock().now().nanoseconds + int(s * 1e9)
        while self.get_clock().now().nanoseconds < end:
            rclpy.spin_once(self, timeout_sec=0.05)

    def _traj(self, joints, keys, do_mirror):
        """Build a timed trajectory: hold a pose, then move so it ARRIVES on the beat."""
        pts = [JointTrajectoryPoint(positions=list(HOME), time_from_start=_dur(0.0))]
        prev = HOME
        for db, pose in keys:
            tgt = mirror(pose) if do_mirror else list(pose)
            t = (COUNT_IN - 1 + db) * self.beat        # arrival time of this beat
            thold = t - MOVE_FRAC * self.beat          # hold prev until the move starts
            if thold > pts[-1].time_from_start.sec + pts[-1].time_from_start.nanosec / 1e9:
                pts.append(JointTrajectoryPoint(positions=list(prev), time_from_start=_dur(thold)))
            pts.append(JointTrajectoryPoint(positions=tgt, time_from_start=_dur(t)))
            prev = tgt
        tr = JointTrajectory(joint_names=joints)
        tr.points = pts
        return tr

    def dance(self):
        total = (COUNT_IN - 1 + 16) * self.beat + 0.5
        self.get_logger().info(f"beat={self.beat:.3f}s  count-in={COUNT_IN}  dance≈{total:.1f}s")
        # publish both arms' full timed trajectories at once; controller plays them back on-beat
        self.lpub.publish(self._traj(LEFT_JOINTS, LEFT_KEYS, do_mirror=False))
        self.rpub.publish(self._traj(RIGHT_JOINTS, RIGHT_KEYS, do_mirror=True))
        self.get_logger().info("trajectories sent — dancing on the beat grid")
        self._spin(total)
        self.get_logger().info("¡Macarena! (on-beat) done")


def main():
    bpm = float(sys.argv[1]) if len(sys.argv) > 1 else 103.0
    rclpy.init()
    n = Synced(bpm)
    try:
        n.dance()
    finally:
        n.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
