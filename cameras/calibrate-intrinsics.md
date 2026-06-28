# Intrinsic calibration (per camera)

UVC cameras ship with **no factory intrinsics**, so each of the three must be
calibrated. Mono/global-shutter or RGB/rolling-shutter — the procedure is the same.

## Target
Print a **ChArUco board** (e.g. 5×7, 30 mm squares) on rigid flat board. ChArUco
beats a plain checkerboard: tolerant of partial views, sub-pixel corners, fewer
images. One board does all three cameras and the hand-eye step.

## Per camera
Bring up just one camera (see `cameras.launch.py`, or run a single node):

```bash
ros2 run v4l2_camera v4l2_camera_node \
  --ros-args -p video_device:=/dev/cam_torso -p image_size:="[1280,800]"
```

> Calibrate at the **resolution you'll actually run** — intrinsics are
> resolution-specific. (1280×800 here; if you infer at 640×400, calibrate at that.)

Run the calibrator against its topics:

```bash
ros2 run camera_calibration cameracalibrator \
  -p charuco --size 7x5 --square 0.030 \
  --charuco_marker_size 0.022 --aruco_dict 5x5_100 \
  --ros-args -r image:=/torso_camera/image_raw -r camera:=/torso_camera
```

`-p charuco` is required for a ChArUco board (`--size` = squares, `--square`/
`--charuco_marker_size` in metres, `--aruco_dict` = the printed dictionary). Without
`-p charuco`, cameracalibrator runs plain-checkerboard detection and will **not** see
the board.

Move the board to cover: all corners/edges of the frame, near + far, and tilted
(±30°). Capture ~20–30 views; the **CALIBRATE** button enables when coverage is
good. **SAVE** writes a tarball with the `CameraInfo` YAML.

> **Verified in sim / fallback.** The ChArUco detector and the calibration engine
> are sim-verified against ground truth: run `python3 cameras/sim_verify_detection.py`
> (real `detectMarkers`+`interpolateCornersCharuco` across poses),
> `sim_verify_charuco_engine.py` (cameracalibrator's `MonoCalibrator` accumulates
> ChArUco samples), and `sim_verify_intrinsics.py` (recovers known K+distortion).
> Note: in the dev VM's `camera_calibration` (Humble) build, the `cameracalibrator`
> GUI's `-p charuco` mode did not reliably subscribe to the image stream; the engine
> itself is correct. If the GUI shows no detections on the real rig, a plain
> **checkerboard** (printed separately, run with `--size 7x5 --square 0.030` and no
> `-p charuco`) is the verified-reliable fallback for intrinsics —
> `sim_verify_calibrator.py` confirms that path end-to-end through the driver.

## Output
Place the resulting YAML at `cameras/calib/<name>.yaml`
(`torso_camera.yaml`, `left_gripper_camera.yaml`, `right_gripper_camera.yaml`).
`cameras.launch.py` loads it via `camera_info_url`, so `camera_info` then carries
the real fx, fy, cx, cy + distortion.

The 70°-ish M12 lens needs only the standard radial-tangential model (default) —
no fisheye model.
