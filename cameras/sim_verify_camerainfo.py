#!/usr/bin/env python3
"""CameraInfo round-trip check (no hardware).

cameras.launch.py points each camera node's `camera_info_url` at a calibration
YAML so that the published `camera_info` topic carries the real fx, fy, cx, cy +
distortion. This verifies that wiring end-to-end on the live ROS graph: write a
YAML with KNOWN K/D, start a real camera driver (image_publisher_node, which reads
camera_info_url exactly like v4l2_camera_node), subscribe to its camera_info, and
assert the message carries the same K/D we wrote.

The YAML is generated in a tempdir, not committed under cameras/calib/, because a
checked-in file there would look like real (hardware-derived) intrinsics.

Requires a sourced ROS 2.
    python3 sim_verify_camerainfo.py
"""
import os
import signal
import subprocess
import tempfile
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import CameraInfo

W, H = 1280, 800
K = [900.0, 0.0, 640.0, 0.0, 900.0, 400.0, 0.0, 0.0, 1.0]
D = [0.05, -0.08, 0.001, 0.0005, 0.0]
NS = "/testcam"

YAML = f"""image_width: {W}
image_height: {H}
camera_name: testcam
camera_matrix:
  rows: 3
  cols: 3
  data: [{', '.join(map(str, K))}]
distortion_model: plumb_bob
distortion_coefficients:
  rows: 1
  cols: 5
  data: [{', '.join(map(str, D))}]
rectification_matrix:
  rows: 3
  cols: 3
  data: [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
projection_matrix:
  rows: 3
  cols: 4
  data: [900.0, 0.0, 640.0, 0.0, 0.0, 900.0, 400.0, 0.0, 0.0, 0.0, 1.0, 0.0]
"""


def kill_group(p, wait=4):
    """Kill the subprocess group. `ros2 run` forks the node child, so p.pid (group
    leader via start_new_session) must be SIGKILLed to be sure the node dies too —
    not just the wrapper. Never pkill -f (would self-match the launching command)."""
    try:
        os.killpg(p.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        p.wait(timeout=wait)
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


class Sink(Node):
    def __init__(self):
        super().__init__("camerainfo_sink")
        self.msg = None
        self.create_subscription(CameraInfo, f"{NS}/camera_info", self._cb, 10)

    def _cb(self, m):
        self.msg = m


def main():
    tmp = tempfile.mkdtemp(prefix="camerainfo_rt_")
    yaml_path = os.path.join(tmp, "testcam.yaml")
    img_path = os.path.join(tmp, "frame.png")
    with open(yaml_path, "w") as f:
        f.write(YAML)
    cv2.imwrite(img_path, np.zeros((H, W, 3), np.uint8))

    # real camera driver reading camera_info_url, just like cameras.launch.py
    proc = subprocess.Popen(
        ["ros2", "run", "image_publisher", "image_publisher_node", img_path,
         "--ros-args", "-r", f"__ns:={NS}", "-p", f"camera_info_url:=file://{yaml_path}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        rclpy.init()
        sink = Sink()
        deadline = sink.get_clock().now().nanoseconds + 25 * 1_000_000_000
        while sink.msg is None and sink.get_clock().now().nanoseconds < deadline:
            rclpy.spin_once(sink, timeout_sec=0.5)
        assert sink.msg is not None, "no CameraInfo received within 25s"

        m = sink.msg
        print(f"received CameraInfo: {m.width}x{m.height}, model={m.distortion_model!r}")
        print(f"  K={list(m.k)}")
        print(f"  D={list(m.d)}")
        assert (m.width, m.height) == (W, H), "resolution mismatch"
        assert m.distortion_model == "plumb_bob", "distortion model mismatch"
        assert np.allclose(m.k, K, atol=1e-6), "K mismatch"
        assert np.allclose(m.d, D, atol=1e-6), "D mismatch"
        print("PASS: camera_info_url round-trips the exact K/D onto the camera_info topic")
    finally:
        rclpy.try_shutdown()
        kill_group(proc)


if __name__ == "__main__":
    main()
