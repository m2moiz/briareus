#!/usr/bin/env python3
"""Full ROS driver pipeline check over a virtual camera (no hardware).

Exercises the REAL driver path the robot uses, end to end, with no physical camera:

    synthetic frames --ffmpeg--> /dev/video10 (v4l2loopback) --> v4l2_camera_node
        --> /sim_cam/image_raw + /sim_cam/camera_info

A moving chessboard is rendered and streamed into a v4l2loopback device; the actual
v4l2_camera_node (the same node cameras.launch.py runs) opens that device and we
assert it publishes image_raw + camera_info at the expected size and rate.

Prerequisites (one-time, need root) — the device must exist and be readable:
    sudo apt-get install -y v4l2loopback-dkms v4l2loopback-utils ffmpeg
    sudo modprobe v4l2loopback devices=1 video_nr=10 card_label=OpenArmSimCam exclusive_caps=1
    sudo chmod 666 /dev/video10

Requires a sourced ROS 2 (v4l2_camera) + ffmpeg.
    python3 sim_verify_v4l2_pipeline.py
"""
import os
import signal
import subprocess
import tempfile
import time
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo

DEV = "/dev/video10"
W, H = 640, 480
NS = "/sim_cam"
COLS, ROWS = 8, 6                  # chessboard squares -> 7x5 interior corners


def render_frames(outdir, n=40):
    """Render a moving 8x6 chessboard (white quiet border) as a frame sequence."""
    sq = 50
    bw, bh = COLS * sq, ROWS * sq
    board = np.zeros((bh, bw), np.uint8)
    for i in range(ROWS):
        for j in range(COLS):
            if (i + j) % 2 == 0:
                board[i * sq:(i + 1) * sq, j * sq:(j + 1) * sq] = 255
    src = np.float32([[0, 0], [bw, 0], [bw, bh], [0, bh]])
    rng = np.random.default_rng(3)
    for k in range(n):
        # translate + perspective-jitter so the calibrator sees varied poses
        cx = W / 2 + 60 * np.cos(2 * np.pi * k / n)
        cy = H / 2 + 40 * np.sin(2 * np.pi * k / n)
        jit = (rng.uniform(-0.08, 0.08, (4, 2)) * [bw, bh]).astype(np.float32)
        dst = np.float32([[cx - bw/2, cy - bh/2], [cx + bw/2, cy - bh/2],
                          [cx + bw/2, cy + bh/2], [cx - bw/2, cy + bh/2]]) + jit
        M = cv2.getPerspectiveTransform(src, dst)
        frame = cv2.warpPerspective(board, M, (W, H), borderValue=255)
        cv2.imwrite(os.path.join(outdir, f"frame_{k:03d}.png"), frame)


def kill_group(p, sig=signal.SIGTERM, wait=4):
    """Kill a subprocess's whole group. `ros2 run` forks the node as a child, so
    p.pid (the group leader, via start_new_session) must be SIGKILLed to be sure the
    node child dies too — not just the wrapper. Never pkill -f (would self-match)."""
    try:
        os.killpg(p.pid, sig)
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
        super().__init__("v4l2_pipeline_sink")
        self.n_img = 0
        self.n_info = 0
        self.dims = None
        self.create_subscription(Image, f"{NS}/image_raw", self._img, 10)
        self.create_subscription(CameraInfo, f"{NS}/camera_info", self._info, 10)

    def _img(self, m):
        self.n_img += 1
        self.dims = (m.width, m.height)

    def _info(self, m):
        self.n_info += 1


def main():
    assert os.path.exists(DEV), f"{DEV} missing — load v4l2loopback (see module docstring)"
    assert os.access(DEV, os.R_OK | os.W_OK), f"{DEV} not accessible — sudo chmod 666 {DEV}"

    tmp = tempfile.mkdtemp(prefix="v4l2_pipe_")
    render_frames(tmp)

    ffmpeg = subprocess.Popen(
        ["ffmpeg", "-loglevel", "error", "-re", "-stream_loop", "-1", "-framerate", "15",
         "-i", os.path.join(tmp, "frame_%03d.png"), "-vf", "format=yuyv422",
         "-f", "v4l2", DEV],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    time.sleep(2.5)                  # let ffmpeg establish the device format first

    node = subprocess.Popen(
        ["ros2", "run", "v4l2_camera", "v4l2_camera_node", "--ros-args",
         "-r", f"__ns:={NS}", "-p", f"video_device:={DEV}",
         "-p", f"image_size:=[{W},{H}]", "-p", "pixel_format:=YUYV"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        rclpy.init()
        sink = Sink()
        t_end = time.time() + 14
        while time.time() < t_end and (sink.n_img < 8 or sink.n_info < 8):
            rclpy.spin_once(sink, timeout_sec=0.2)

        print(f"received {sink.n_img} image_raw, {sink.n_info} camera_info on {NS}")
        print(f"  image dims: {sink.dims}")
        assert sink.n_img >= 8, f"v4l2_camera_node did not stream images ({sink.n_img})"
        assert sink.n_info >= 8, f"no camera_info published ({sink.n_info})"
        assert sink.dims == (W, H), f"image dims {sink.dims} != {(W, H)}"
        print("PASS: ffmpeg -> v4l2loopback -> v4l2_camera_node streams image_raw + camera_info")
    finally:
        rclpy.try_shutdown()
        kill_group(node)
        kill_group(ffmpeg)


if __name__ == "__main__":
    main()
