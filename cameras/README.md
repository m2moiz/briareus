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

## Verified vs. hardware-only
The **toolchain install** (`provision-cameras.sh`) and the launch/xacro **parse**
are verified in the dev VM. The **calibration itself** — intrinsics, hand-eye, and
the udev port mapping — runs only on the **real rig** (no cameras in sim).
