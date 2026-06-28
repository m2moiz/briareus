# OpenArm camera calibration (perception / grasping)

Calibrates the three UVC cameras (torso + 2 grippers) so their **intrinsics** and
**extrinsics** are known and published in `tf` — what classical perception/grasping
needs. Run on the Linux box wired to the cameras + arm.

## Order of operations
1. **Install toolchain** — `bash cameras/provision-cameras.sh`
   (apt: v4l2_camera, camera_calibration, image_pipeline, v4l-utils; source: easy_handeye2)
2. **Pin the cameras** — `bash cameras/discover-cameras.sh` → fill USB port paths into
   `99-openarm-cameras.rules` → install to `/etc/udev/rules.d/` + reload → `/dev/cam_*`
3. **Intrinsics** — per camera, `cameras/calibrate-intrinsics.md` → `cameras/calib/<name>.yaml`
4. **Stream with calibration** — `ros2 launch cameras/cameras.launch.py`
5. **Extrinsics (hand-eye)** — `cameras/calibrate-handeye.md` (eye-in-hand grippers,
   eye-to-hand torso; move-stop-capture for the rolling-shutter RGB torso cam)
6. **Into the robot** — paste transforms into `openarm-cameras.xacro`, include from the
   robot xacro → `tf` publishes each camera's optical frame.

## Files
| File | Role |
|---|---|
| `provision-cameras.sh` | install the toolchain (verified to build on Humble/arm64) |
| `discover-cameras.sh` | print each camera's USB port path + formats |
| `99-openarm-cameras.rules` | udev: pin 3 identical cams to stable `/dev/cam_*` |
| `cameras.launch.py` | bring up all 3 cameras with calibration |
| `calibrate-intrinsics.md` | ChArUco intrinsic calibration runbook |
| `calibrate-handeye.md` | easy_handeye2 extrinsic runbook |
| `openarm-cameras.xacro` | camera tf frames (paste calibrated transforms) |
| `sim_verify_*.py` | no-hardware regression tests (see below) |

## Sim verification suite (`sim_verify_*.py`)
Run with a sourced ROS 2 in the dev VM. They verify the **pipeline, wiring and math**
against known ground truth — not the real cameras' actual parameters.

| Test | Verifies |
|---|---|
| `sim_verify_intrinsics.py` | `calibrateCameraCharuco` recovers a known K + distortion |
| `sim_verify_detection.py` | real `detectMarkers`+`interpolateCornersCharuco` find the board across poses |
| `sim_verify_charuco_engine.py` | cameracalibrator's `MonoCalibrator` accumulates ChArUco samples |
| `sim_verify_handeye.py` | `calibrateHandEye` (PARK) recovers a known gripper→camera transform |
| `sim_verify_handeye_launch.py` | `easy_handeye2` calibrate.launch.py wires the eye_in_hand config |
| `sim_verify_camerainfo.py` | `camera_info_url` round-trips K/D onto the `camera_info` topic |
| `sim_verify_v4l2_pipeline.py` | real `v4l2_camera_node` streams image_raw+camera_info off a virtual device |
| `sim_verify_calibrator.py` | the `cameracalibrator` binary detects + accumulates over the v4l2 stream |
| `sim_verify_udev.py` | the udev naming rules are well-formed and declare all three symlinks |

The v4l2 tests need a one-time `v4l2loopback` setup (root) — see each file's docstring.

## Verified vs. hardware-only
**Sim-verified (dev VM):** toolchain install, launch/xacro parse, the calibration +
hand-eye **math** (recovers known ground truth), ChArUco **detection**, the full
**driver pipeline** (virtual device → `v4l2_camera_node` → `cameracalibrator`),
`camera_info_url` plumbing, udev syntax, and the easy_handeye2 launch wiring.

**Hardware-only (real rig):** the cameras' actual intrinsics/distortion values, the
udev USB **port mapping**, rolling-shutter behavior, and the live hand-eye capture —
sim proves the machinery works, not what the real sensors measure.
