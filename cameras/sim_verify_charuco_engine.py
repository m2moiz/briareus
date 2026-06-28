#!/usr/bin/env python3
"""ChArUco calibration-engine check (no hardware, no GUI).

sim_verify_calibrator.py runs the cameracalibrator *binary* end-to-end, but streams
a plain chessboard — the binary's `-p charuco` GUI mode does not reliably subscribe
in this ROS 2 Humble build (see calibrate-intrinsics.md note). This test verifies
the piece that matters for the ChArUco workflow: cameracalibrator's own calibration
engine (camera_calibration.MonoCalibrator) detects a ChArUco board and accumulates
samples, using the EXACT board params the runbook documents
(7x5, 30 mm square, 22 mm marker, dict 5x5_100, `-p charuco`).

Renders moving ChArUco frames and drives MonoCalibrator.handle_msg directly, then
asserts several samples accumulate with real frame-coverage spread.

Requires a sourced ROS 2 (camera_calibration + cv_bridge).
    python3 sim_verify_charuco_engine.py
"""
import numpy as np
import cv2
from cv_bridge import CvBridge
from camera_calibration.calibrator import MonoCalibrator, ChessboardInfo, Patterns

W, H = 640, 480
MIN_SAMPLES = 4


def render_frames(n=28):
    aruco = cv2.aruco
    d = aruco.getPredefinedDictionary(aruco.DICT_5X5_100)
    board = aruco.CharucoBoard_create(7, 5, 0.030, 0.022, d)
    img = board.draw((504, 360), marginSize=0, borderBits=1)   # big, crisp markers
    bh, bw = img.shape
    src = np.float32([[0, 0], [bw, 0], [bw, bh], [0, bh]])
    rng = np.random.default_rng(11)
    frames = []
    for k in range(n):
        t = 2 * np.pi * k / n
        cx, cy = W / 2 + 55 * np.cos(t), H / 2 + 45 * np.sin(t)
        s = 0.82 + 0.16 * np.sin(2 * t)
        jit = (rng.uniform(-0.05, 0.05, (4, 2)) * [bw, bh]).astype(np.float32)
        dst = np.float32([[cx - bw*s/2, cy - bh*s/2], [cx + bw*s/2, cy - bh*s/2],
                          [cx + bw*s/2, cy + bh*s/2], [cx - bw*s/2, cy + bh*s/2]]) + jit
        M = cv2.getPerspectiveTransform(src, dst)
        gray = cv2.warpPerspective(img, M, (W, H), borderValue=255)
        frames.append(cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR))
    return frames


def main():
    board = ChessboardInfo(pattern="charuco", n_cols=7, n_rows=5,
                           dim=0.030, marker_size=0.022, aruco_dict="5x5_100")
    cal = MonoCalibrator([board], pattern=Patterns.ChArUco)
    br = CvBridge()

    frames = render_frames()
    for f in frames:
        cal.handle_msg(br.cv2_to_imgmsg(f, "bgr8"))

    n = len(cal.db)
    params = [s[0] for s in cal.db]            # each is [p_x, p_y, p_size, skew]
    print(f"charuco engine accumulated {n} samples (threshold {MIN_SAMPLES})")
    for p in params[:3] + params[-1:]:
        print(f"  p_x={p[0]:.3f} p_y={p[1]:.3f} p_size={p[2]:.3f} skew={p[3]:.3f}")
    assert n >= MIN_SAMPLES, f"only {n} charuco samples accumulated"
    pxs = [p[0] for p in params]
    pys = [p[1] for p in params]
    assert max(pxs) - min(pxs) > 0.1 or max(pys) - min(pys) > 0.1, \
        "samples lack coverage spread — board not tracked across the view"
    print("PASS: MonoCalibrator detected the ChArUco board and accumulated samples")


if __name__ == "__main__":
    main()
