#!/usr/bin/env python3
"""Bimanual drum beat — alternating toms, timed to the beat grid.

Each stick strike ARRIVES (tip down) on its beat. Built as one timed trajectory
per arm (waypoints stamped at exact beat times) and handed to the trajectory
controller, which replays on precise timestamps, so strikes land on the beat.
(Same approach as macarena_synced.py: live MoveIt planning is too slow to hit fast
strikes, so we play back pre-built timed trajectories.)

The two arms trade strikes left-right-left-right on a steady 8th-note pulse, like a
hand-to-hand tom groove. A 4-beat count-in matches the drum loop so you can start
both together.

Run inside the VM with the trajectory controllers up (e.g. after `scripts/drums.sh`,
which brings up scripts/drums.launch.py):
    python3 drumbeat.py [BPM] [BARS]      # defaults: 90 BPM, 4 bars
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

# right arm = left arm mirrored (negate every joint except the elbow, j4)
MIRROR = [-1, -1, -1, +1, -1, -1, -1]

# Poses for the LEFT arm (j1..j7). The arm reaches forward and a little out so the
# two sticks sit over separate drums; a strike flicks the elbow + wrist down.
HOME = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
READY = [0.25, -1.0, 0.0, 0.90, 0.0, 0.60, 0.0]   # stick raised over the drum
STRIKE = [0.25, -1.0, 0.0, 1.28, 0.0, 0.92, 0.0]  # elbow + wrist flick: tip comes down

COUNT_IN = 4          # beats of count-in (matches the drum loop)
FLICK = 0.18          # fraction of a beat for the down (and up) stroke; fast, snappy


def mirror(p):
    return [s * v for s, v in zip(MIRROR, p)]


def _dur(t):
    t = max(0.0, t)
    return Duration(sec=int(t), nanosec=int((t % 1.0) * 1e9))


class Drummer(Node):
    def __init__(self, bpm=90.0, bars=4):
        super().__init__("drumbeat")
        self.beat = 60.0 / bpm
        self.bars = bars
        self.lpub = self.create_publisher(JointTrajectory, LTOPIC, 10)
        self.rpub = self.create_publisher(JointTrajectory, RTOPIC, 10)
        self._spin(1.0)

    def _spin(self, s):
        end = self.get_clock().now().nanoseconds + int(s * 1e9)
        while self.get_clock().now().nanoseconds < end:
            rclpy.spin_once(self, timeout_sec=0.05)

    def _strike_times(self, offset_eighths):
        """Hit times (seconds) for one arm: every other 8th note, starting at
        offset_eighths (0 for the left arm, 1 for the right). 8 eighths per bar."""
        eighth = self.beat / 2.0
        t0 = COUNT_IN * self.beat
        return [t0 + s * eighth for s in range(offset_eighths, self.bars * 8, 2)]

    def _traj(self, joints, hits, do_mirror):
        """Build a timed trajectory: hold READY, flick to STRIKE arriving on the
        beat, then recover to READY, for each hit time."""
        ready = mirror(READY) if do_mirror else list(READY)
        strike = mirror(STRIKE) if do_mirror else list(STRIKE)
        flick = FLICK * self.beat
        # (time, pose) waypoints: raise to READY during the count-in, then flick
        # down to STRIKE on each beat and recover to READY.
        raw = [(0.0, list(HOME)), (COUNT_IN * self.beat - flick, ready)]
        for th in hits:
            raw += [(th - flick, ready), (th, strike), (th + flick, ready)]
        # keep timestamps strictly increasing — the controller rejects duplicates
        # (the first beat's pre-position can coincide with the count-in waypoint).
        pts, last_t = [], -1.0
        for t, pose in raw:
            if t <= last_t + 1e-3:
                continue
            pts.append(JointTrajectoryPoint(positions=pose, time_from_start=_dur(t)))
            last_t = t
        tr = JointTrajectory(joint_names=joints)
        tr.points = pts
        return tr

    def play(self):
        total = COUNT_IN * self.beat + self.bars * 4 * self.beat + 1.0
        self.get_logger().info(
            f"beat={self.beat:.3f}s  count-in={COUNT_IN}  bars={self.bars}  run≈{total:.1f}s")
        self.lpub.publish(self._traj(LEFT_JOINTS, self._strike_times(0), do_mirror=False))
        self.rpub.publish(self._traj(RIGHT_JOINTS, self._strike_times(1), do_mirror=True))
        self.get_logger().info("trajectories sent — drumming on the beat grid")
        self._spin(total)
        self.get_logger().info("beat done")


def main():
    bpm = float(sys.argv[1]) if len(sys.argv) > 1 else 90.0
    bars = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    rclpy.init()
    n = Drummer(bpm, bars)
    try:
        n.play()
    finally:
        n.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
