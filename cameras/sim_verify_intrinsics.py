#!/usr/bin/env python3
"""Simulated intrinsic calibration check (no hardware).

Project a ChArUco board with a KNOWN camera matrix K and distortion D at many
poses (i.e. simulate what the camera would observe), then run the SAME solver the
real pipeline uses (cv2.aruco.calibrateCameraCharuco) and assert it recovers K, D.

Verifies the intrinsic calibration math + our API usage against ground truth.
    python3 sim_verify_intrinsics.py
"""
import numpy as np
import cv2

W, H = 1280, 800
K_GT = np.array([[900.0, 0, 640.0], [0, 900.0, 400.0], [0, 0, 1.0]])
D_GT = np.array([0.05, -0.08, 0.001, 0.0005, 0.0])     # mild radial-tangential


def main():
    aruco = cv2.aruco
    dictionary = aruco.getPredefinedDictionary(aruco.DICT_5X5_100)
    board = aruco.CharucoBoard_create(7, 5, 0.030, 0.022, dictionary)
    objp = board.chessboardCorners.reshape(-1, 3).astype(np.float64)
    ids_all = np.arange(len(objp)).reshape(-1, 1).astype(np.int32)

    rng = np.random.default_rng(1)
    corners, ids = [], []
    for _ in range(30):
        rvec = rng.uniform(-0.4, 0.4, 3)
        tvec = np.array([rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05),
                         rng.uniform(0.45, 0.7)])
        img, _ = cv2.projectPoints(objp, rvec, tvec, K_GT, D_GT)
        img = img.reshape(-1, 2)
        m = (img[:, 0] >= 0) & (img[:, 0] < W) & (img[:, 1] >= 0) & (img[:, 1] < H)
        if m.sum() < 6:
            continue
        corners.append(img[m].reshape(-1, 1, 2).astype(np.float32))
        ids.append(ids_all[m].reshape(-1, 1))

    rms, K, D, _, _ = aruco.calibrateCameraCharuco(corners, ids, board, (W, H), None, None)
    efx, efy = abs(K[0, 0] - K_GT[0, 0]), abs(K[1, 1] - K_GT[1, 1])
    ecx, ecy = abs(K[0, 2] - K_GT[0, 2]), abs(K[1, 2] - K_GT[1, 2])
    ed = np.abs(D.ravel()[:5] - D_GT).max()
    print(f"intrinsics recovery ({len(corners)} views): rms reproj = {rms:.4f} px")
    print(f"  fx err={efx:.3f}  fy err={efy:.3f}  cx err={ecx:.3f}  cy err={ecy:.3f}  |dist| err={ed:.4f}")
    assert efx < 1 and efy < 1 and ecx < 1 and ecy < 1 and ed < 0.01, "FAILED to recover intrinsics"
    print("PASS: calibrateCameraCharuco recovered the known camera matrix + distortion")


if __name__ == "__main__":
    main()
