#!/usr/bin/env python3
"""Simulated ChArUco DETECTION check (no hardware).

sim_verify_intrinsics.py exercises the calibration SOLVER on synthetic corner
coordinates from cv2.projectPoints — it never renders pixels, so it does not prove
the board can actually be *detected* in an image. This closes that gap: render a
real ChArUco board image, warp it to many simulated viewpoints, and run the REAL
detector the calibrator uses (cv2.aruco.detectMarkers + interpolateCornersCharuco).
Assert detection succeeds across every pose.

    python3 sim_verify_detection.py [out_dir]   # out_dir -> dump annotated PNGs
"""
import sys
import numpy as np
import cv2

SQX, SQY = 7, 5                     # board squares (matches calibrate-intrinsics.md)
SQUARE_M, MARKER_M = 0.030, 0.022
N_INTERIOR = (SQX - 1) * (SQY - 1)  # interior chessboard corners ChArUco can return


def render_board(board, square_px=120, margin_px=90):
    """Render the board flat, on a white canvas so markers keep a quiet zone
    (the ArUco detector needs white space around the outer markers)."""
    w, h = SQX * square_px, SQY * square_px
    img = board.draw((w, h), marginSize=0, borderBits=1)
    canvas = np.full((h + 2 * margin_px, w + 2 * margin_px), 255, np.uint8)
    canvas[margin_px:margin_px + h, margin_px:margin_px + w] = img
    return canvas


def warp_to_pose(canvas, rng):
    """Random mild perspective warp simulating a tilted/rotated viewpoint."""
    H, W = canvas.shape
    src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    jitter = (rng.uniform(-0.18, 0.18, (4, 2)) * [W, H]).astype(np.float32)
    pad = int(0.25 * max(W, H))
    dst = src + jitter + pad
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(canvas, M, (W + 2 * pad, H + 2 * pad), borderValue=255)


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else None
    aruco = cv2.aruco
    dictionary = aruco.getPredefinedDictionary(aruco.DICT_5X5_100)
    board = aruco.CharucoBoard_create(SQX, SQY, SQUARE_M, MARKER_M, dictionary)

    canvas = render_board(board)

    # Baseline: detect on the flat board so pose thresholds are relative to it
    # (avoids depending on the exact embedded-marker count of the board).
    _, i0, _ = aruco.detectMarkers(canvas, dictionary)
    assert i0 is not None and len(i0) > 0, "could not detect even the flat board"
    base = len(i0)
    print(f"flat board: {base} ArUco markers detected (baseline)")

    rng = np.random.default_rng(7)
    n_poses = 12
    ok = 0
    min_m, min_c = base, N_INTERIOR
    for i in range(n_poses):
        view = canvas if i == 0 else warp_to_pose(canvas, rng)
        corners, ids, _ = aruco.detectMarkers(view, dictionary)
        if ids is None or len(ids) == 0:
            print(f"  pose {i:2d}: NO markers detected")
            continue
        _, ch_corners, ch_ids = aruco.interpolateCornersCharuco(corners, ids, view, board)
        nm = len(ids)
        nc = 0 if ch_ids is None else len(ch_ids)
        min_m, min_c = min(min_m, nm), min(min_c, nc)
        usable = nm >= 0.6 * base and nc >= 6
        ok += usable
        print(f"  pose {i:2d}: {nm:2d}/{base} markers, {nc:2d}/{N_INTERIOR} charuco corners"
              f"  {'OK' if usable else 'WEAK'}")
        if outdir:
            vis = cv2.cvtColor(view, cv2.COLOR_GRAY2BGR)
            aruco.drawDetectedMarkers(vis, corners, ids)
            if ch_ids is not None:
                aruco.drawDetectedCornersCharuco(vis, ch_corners, ch_ids, (0, 0, 255))
            cv2.imwrite(f"{outdir}/detect_pose_{i:02d}.png", vis)

    print(f"detection: {ok}/{n_poses} poses usable "
          f"(worst case {min_m} markers, {min_c} corners)")
    assert ok == n_poses, "detector FAILED on at least one pose"
    print("PASS: detectMarkers + interpolateCornersCharuco found the board across all poses")


if __name__ == "__main__":
    main()
