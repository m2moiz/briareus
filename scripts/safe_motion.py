"""Shared motion-safety helper — pace trajectories to the calibrated limits.

Motion scripts use it like:

    from safe_motion import Limits
    lim = Limits.load()                                   # reads motion_limits.yaml
    secs = lim.duration(start, goal, joints, base=1.0)    # safe trajectory time

`duration()` returns a time long enough that no joint exceeds its calibrated
safe velocity (further scaled by the global speed_scale), with `base` as a floor.
If no calibration file exists yet, it falls back to deliberately slow defaults so
scripts still run safely — just run calibrate.py first to tune them.
"""
import os
import yaml

_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "motion_limits.yaml")


class Limits:
    def __init__(self, speed_scale=0.20, joints=None, measured=False):
        self.speed_scale = float(speed_scale)
        self.joints = joints or {}        # joint name -> {"safe_velocity": rad/s}
        self.measured = bool(measured)

    @classmethod
    def load(cls, path=None):
        try:
            d = yaml.safe_load(open(path or _DEFAULT))
            return cls(d.get("speed_scale", 0.20), d.get("joints", {}), d.get("measured", False))
        except Exception:
            return cls()                  # conservative: slow, unmeasured

    def safe_velocity(self, joint):
        j = self.joints.get(joint)
        return float(j["safe_velocity"]) if j and "safe_velocity" in j else 0.5

    def duration(self, start, goal, joints, base=1.0):
        """Seconds so no joint exceeds safe_velocity*speed_scale; never below `base`."""
        need = float(base)
        for s, g, jn in zip(start, goal, joints):
            eff_v = max(self.safe_velocity(jn) * self.speed_scale, 1e-3)
            need = max(need, abs(g - s) / eff_v)
        return need
