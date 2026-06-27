#!/usr/bin/env python3
"""Safe startup calibration + motion-limit characterization for OpenArm.

Run ONCE before the motion scripts (wiggle / bimanual_sequence / macarena). It
probes the arm slowly and writes ``motion_limits.yaml`` — a conservative,
per-joint safe velocity + a global speed scale that the motion scripts read so
their trajectories never outrun what the hardware can do under gravity.

What it does, slowly and in a controlled way:
  1. PREFLIGHT — wait for every controller to be active; read /joint_states;
     verify the arm is at home within ±0.05 rad (OpenArm's own tolerance). A
     joint far from 0 means the motor zero is wrong: STOP and re-run OpenArm's
     zero-position calibration (lerobot-calibrate / Damiao SaveZero) first.
  2. GRAVITY PROBE — hold home and read joint effort (if the effort state
     interface is published) → the static gravity torque each joint must hold.
  3. ARTICULATION SWEEP — move each joint a small amount (±0.1 rad) very slowly,
     measure tracking error (commanded vs measured) and peak effort, and derive
     a safe max velocity per joint.
  4. WRITE motion_limits.yaml.

SIM vs REAL — be honest: the mock_components sim has NO gravity, effort, or
tracking error (positions are perfect). On sim this VALIDATES the motion path
and writes CONSERVATIVE DEFAULTS marked ``measured: false``. The real
gravity/tracking tuning (``measured: true``) only happens on hardware.

    python3 calibrate.py            # full slow calibration -> motion_limits.yaml
    python3 calibrate.py --check    # preflight only (no motion)
"""
import os
import sys
import yaml

import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Duration
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from ament_index_python.packages import get_package_share_directory

ARMS = {
    "left":  ("/left_joint_trajectory_controller/joint_trajectory",
              [f"openarm_left_joint{i}" for i in range(1, 8)]),
    "right": ("/right_joint_trajectory_controller/joint_trajectory",
              [f"openarm_right_joint{i}" for i in range(1, 8)]),
}
HOME_TOL = 0.05        # rad — OpenArm's documented zero tolerance
SWEEP = 0.10           # rad — tiny, safe articulation test around home
TEST_VEL = 0.20        # rad/s — deliberately slow probe speed
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "motion_limits.yaml")


def _dur(s):
    return Duration(sec=int(s), nanosec=int((s % 1.0) * 1e9))


class Calibrator(Node):
    def __init__(self):
        super().__init__("openarm_calibrate")
        self.pubs = {s: self.create_publisher(JointTrajectory, t, 10)
                     for s, (t, _) in ARMS.items()}
        self.state = {}     # joint -> (position, effort)
        self.create_subscription(JointState, "/joint_states", self._on_state, 10)
        self._max_vel = self._load_urdf_max_vel()
        self._spin(1.5)     # discovery + first /joint_states

    # ---------- helpers ----------
    def _on_state(self, msg):
        for i, n in enumerate(msg.name):
            eff = msg.effort[i] if i < len(msg.effort) else None
            self.state[n] = (msg.position[i] if i < len(msg.position) else None, eff)

    def _spin(self, seconds):
        end = self.get_clock().now().nanoseconds + int(seconds * 1e9)
        while self.get_clock().now().nanoseconds < end:
            rclpy.spin_once(self, timeout_sec=0.05)

    def _load_urdf_max_vel(self):
        """Per-joint max_velocity from joint_limits.yaml (fall back to 1.0)."""
        try:
            share = get_package_share_directory("openarm_bimanual_moveit_config")
            d = yaml.safe_load(open(f"{share}/config/openarm_v2.0/joint_limits.yaml"))
            jl = d.get("joint_limits", d)
            return {k: float(v.get("max_velocity", 1.0)) for k, v in jl.items()}
        except Exception as e:
            self.get_logger().warn(f"could not read joint_limits.yaml: {e}")
            return {}

    def _move_joint(self, side, joints, idx, delta, seconds):
        """Command one joint to home+delta, others held at current, over `seconds`."""
        cur = [self.state.get(j, (0.0, None))[0] or 0.0 for j in joints]
        target = list(cur)
        target[idx] = cur[idx] + delta
        traj = JointTrajectory(joint_names=joints)
        traj.points = [JointTrajectoryPoint(positions=target, time_from_start=_dur(seconds))]
        self.pubs[side].publish(traj)
        self._spin(seconds + 0.4)
        return target

    # ---------- steps ----------
    def preflight(self):
        ok = True
        if not self.state:
            self.get_logger().error("no /joint_states — is the robot bringup running?")
            return False
        self.get_logger().info("PREFLIGHT — checking home tolerance (±0.05 rad):")
        for _, joints in ARMS.values():
            for j in joints:
                pos = self.state.get(j, (None, None))[0]
                if pos is None:
                    self.get_logger().error(f"  {j}: NO STATE")
                    ok = False
                elif abs(pos) > HOME_TOL:
                    self.get_logger().error(
                        f"  {j}: {pos:+.3f} rad — OUT OF TOLERANCE → re-run motor zeroing")
                    ok = False
                else:
                    self.get_logger().info(f"  {j}: {pos:+.3f} rad ok")
        return ok

    def gravity_probe(self):
        efforts = {j: self.state.get(j, (None, None))[1]
                   for _, joints in ARMS.values() for j in joints}
        have = any(e is not None and e != 0.0 for e in efforts.values())
        if have:
            self.get_logger().info("GRAVITY — static effort at home (N·m):")
            for j, e in efforts.items():
                if e is not None:
                    self.get_logger().info(f"  {j}: {e:+.2f}")
        else:
            self.get_logger().warn("GRAVITY — no effort feedback (mock sim?) → defaults only")
        return efforts, have

    def sweep(self):
        """Slow ±SWEEP on each joint; record tracking error + peak effort."""
        results = {}
        self.get_logger().info("ARTICULATION SWEEP — slow ±0.1 rad per joint:")
        for side, (_, joints) in ARMS.items():
            for idx, j in enumerate(joints):
                t = max(SWEEP / TEST_VEL, 0.8)
                target = self._move_joint(side, joints, idx, SWEEP, t)
                meas, eff = self.state.get(j, (None, None))
                err = abs((meas if meas is not None else target[idx]) - target[idx])
                self._move_joint(side, joints, idx, -SWEEP, t)  # return
                vmax = self._max_vel.get(j, 1.0)
                # safe velocity: 25% of rated, halved again if tracking is poor,
                # hard-capped at 1.0 rad/s for a first hardware run.
                margin = 0.25 if err < 0.05 else 0.12
                safe = min(vmax * margin, 1.0)
                results[j] = {"safe_velocity": round(safe, 3),
                              "tracking_error": round(err, 4),
                              "peak_effort": (round(eff, 2) if eff is not None else None)}
                self.get_logger().info(f"  {j}: err={err:.3f} → safe_vel={safe:.2f} rad/s")
        return results

    def run(self, check_only=False):
        if not self.preflight():
            self.get_logger().error("PREFLIGHT FAILED — fix zeroing/bringup before motion.")
            return 1
        if check_only:
            self.get_logger().info("preflight OK (--check, no motion).")
            return 0
        _, measured = self.gravity_probe()
        joints = self.sweep()
        cfg = {
            "schema": 1,
            "measured": bool(measured),   # False on mock sim → defaults only
            "speed_scale": 0.25 if measured else 0.20,  # global; dial up after first runs
            "joints": joints,
            "note": ("measured on real hardware" if measured else
                     "SIM DEFAULTS — no gravity/effort; re-run on hardware to tune"),
        }
        with open(OUT, "w") as f:
            yaml.safe_dump(cfg, f, sort_keys=False)
        self.get_logger().info(f"wrote {OUT}  (measured={measured}, "
                               f"speed_scale={cfg['speed_scale']})")
        return 0


def main():
    rclpy.init()
    node = Calibrator()
    try:
        rc = node.run(check_only="--check" in sys.argv)
    finally:
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(rc)


if __name__ == "__main__":
    main()
