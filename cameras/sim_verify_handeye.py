#!/usr/bin/env python3
"""Simulated hand-eye calibration check (no hardware).

Synthesize a sequence with a KNOWN gripper->camera transform X and a fixed
base->target M: for random arm poses G (base_T_gripper), the target's pose in the
camera is exactly target_T_cam = X^-1 · G^-1 · M. Feed those to the SAME call the
real pipeline uses (cv2.calibrateHandEye) and assert it recovers X.

Verifies the hand-eye math + our API usage end-to-end against ground truth.
    python3 sim_verify_handeye.py
"""
import numpy as np
import cv2


def rand_T(rng, tscale=0.4):
    R, _ = cv2.Rodrigues(rng.uniform(-1.0, 1.0, 3))
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = rng.uniform(-tscale, tscale, 3)
    return T


def main():
    rng = np.random.default_rng(0)
    X = rand_T(rng)                 # ground-truth gripper_T_cam (calibrateHandEye output)
    M = rand_T(rng)                 # fixed base_T_target
    Xi = np.linalg.inv(X)

    Rg2b, tg2b, Rt2c, tt2c = [], [], [], []
    for _ in range(15):
        G = rand_T(rng)             # base_T_gripper (forward kinematics)
        target_T_cam = Xi @ np.linalg.inv(G) @ M
        Rg2b.append(G[:3, :3]); tg2b.append(G[:3, 3].reshape(3, 1))
        Rt2c.append(target_T_cam[:3, :3]); tt2c.append(target_T_cam[:3, 3].reshape(3, 1))

    # PARK/ANDREFF/HORAUD recover this exactly; TSAI is markedly worse even on
    # noise-free data (33 mm vs 0 mm in sim) — prefer PARK on real data too.
    R_out, t_out = cv2.calibrateHandEye(Rg2b, tg2b, Rt2c, tt2c,
                                        method=cv2.CALIB_HAND_EYE_PARK)
    err_t = np.linalg.norm(t_out.ravel() - X[:3, 3]) * 1000.0
    err_R = np.degrees(np.arccos(np.clip((np.trace(R_out.T @ X[:3, :3]) - 1) / 2, -1, 1)))
    print(f"hand-eye recovery: translation err = {err_t:.4f} mm, rotation err = {err_R:.4f} deg")
    assert err_t < 1.0 and err_R < 0.1, "FAILED to recover the known transform"
    print("PASS: cv2.calibrateHandEye recovered the known gripper->camera transform")


if __name__ == "__main__":
    main()
