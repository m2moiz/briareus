#!/usr/bin/env python3
"""cameracalibrator detection check over a virtual camera (no hardware).

Runs the ACTUAL `ros2 run camera_calibration cameracalibrator` binary — the tool
calibrate-intrinsics.md tells the operator to use — against a live v4l2 stream and
confirms it detects the board and accumulates calibration samples:

    moving chessboard --ffmpeg--> /dev/video10 --> v4l2_camera_node
        --> /sim_cam/image_raw --> cameracalibrator (--size 7x5 --square 0.030)

The calibrator prints "*** Added sample N, p_x=.. p_y=.. p_size=.. skew=.." each
time it accepts a detected board pose; we assert several samples accumulate with
varied frame coverage. cameracalibrator opens an OpenCV GUI, so it runs under
xvfb-run (a virtual display).

Prerequisites (one-time, need root):
    sudo apt-get install -y v4l2loopback-dkms v4l2loopback-utils ffmpeg xvfb
    sudo modprobe v4l2loopback devices=1 video_nr=10 card_label=OpenArmSimCam exclusive_caps=1
    sudo chmod 666 /dev/video10

Requires a sourced ROS 2 (v4l2_camera + camera_calibration) + ffmpeg + xvfb.
    python3 sim_verify_calibrator.py
"""
import os
import re
import signal
import subprocess
import tempfile
import time
import numpy as np
import cv2

DEV = "/dev/video10"
W, H = 640, 480
NS = "/sim_cam"
COLS, ROWS = 8, 6                  # 8x6 squares -> 7x5 interior corners (--size 7x5)
RUN_SECONDS = 28
MIN_SAMPLES = 8


def render_frames(outdir, n=40):
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
        cx = W / 2 + 70 * np.cos(2 * np.pi * k / n)
        cy = H / 2 + 50 * np.sin(2 * np.pi * k / n)
        jit = (rng.uniform(-0.07, 0.07, (4, 2)) * [bw, bh]).astype(np.float32)
        dst = np.float32([[cx - bw/2, cy - bh/2], [cx + bw/2, cy - bh/2],
                          [cx + bw/2, cy + bh/2], [cx - bw/2, cy + bh/2]]) + jit
        M = cv2.getPerspectiveTransform(src, dst)
        cv2.imwrite(os.path.join(outdir, f"frame_{k:03d}.png"),
                    cv2.warpPerspective(board, M, (W, H), borderValue=255))


def main():
    assert os.path.exists(DEV), f"{DEV} missing — load v4l2loopback (see docstring)"
    assert os.access(DEV, os.R_OK | os.W_OK), f"{DEV} not accessible — sudo chmod 666 {DEV}"

    tmp = tempfile.mkdtemp(prefix="calib_")
    render_frames(tmp)
    log = os.path.join(tmp, "calib.log")

    ffmpeg = subprocess.Popen(
        ["ffmpeg", "-loglevel", "error", "-re", "-stream_loop", "-1", "-framerate", "15",
         "-i", os.path.join(tmp, "frame_%03d.png"), "-vf", "format=yuyv422", "-f", "v4l2", DEV],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)
    node = subprocess.Popen(
        ["ros2", "run", "v4l2_camera", "v4l2_camera_node", "--ros-args",
         "-r", f"__ns:={NS}", "-p", f"video_device:={DEV}",
         "-p", f"image_size:=[{W},{H}]", "-p", "pixel_format:=YUYV"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)

    # the documented operator command, under a virtual display for the GUI
    with open(log, "w") as lf:
        calib = subprocess.Popen(
            ["xvfb-run", "-a", "ros2", "run", "camera_calibration", "cameracalibrator",
             "--size", "7x5", "--square", "0.030",
             "--ros-args", "-r", f"image:={NS}/image_raw", "-r", f"camera:={NS}"],
            stdout=lf, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            time.sleep(RUN_SECONDS)
        finally:
            # clean SIGINT to the whole xvfb-run group (our own group, precise)
            os.killpg(os.getpgid(calib.pid), signal.SIGINT)
            try:
                calib.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(calib.pid), signal.SIGKILL)
            node.terminate(); ffmpeg.terminate()
            for p in (node, ffmpeg):
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()

    text = open(log).read()
    samples = re.findall(r"Added sample (\d+), p_x = ([\d.]+), p_y = ([\d.]+)", text)
    n = len(samples)
    print(f"cameracalibrator accumulated {n} samples (threshold {MIN_SAMPLES})")
    for s in samples[:3] + samples[-1:]:
        print(f"  sample {s[0]}: p_x={s[1]} p_y={s[2]}")
    assert n >= MIN_SAMPLES, f"only {n} samples accumulated; detection likely failed"
    pxs = [float(s[1]) for s in samples]
    pys = [float(s[2]) for s in samples]
    assert max(pxs) - min(pxs) > 0.1 and max(pys) - min(pys) > 0.1, \
        "samples lack frame coverage spread — board not really tracked across the view"
    print("PASS: cameracalibrator detected the board and accumulated samples over the v4l2 stream")


if __name__ == "__main__":
    main()
