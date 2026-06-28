# Extrinsic (hand-eye) calibration

Do this **after** intrinsics. Two configurations — the wrist cams and the torso
cam are mirror-image rigs:

| Camera | Config | Solves for | Target | Camera |
|---|---|---|---|---|
| gripper cams | **eye-in-hand** | camera → end-effector | fixed in workspace | moves with arm |
| torso cam | **eye-to-hand** | camera → base | on a gripper | fixed |

Tool: **`easy_handeye2`** (built by `provision-cameras.sh`). It records, at each
arm pose, the FK pose (from `tf`) + the ChArUco pose (from `solvePnP`), then solves
`AX=XB`.

## Setup
1. A ChArUco/ArUco target the camera can see, and an ArUco tracker publishing the
   target's pose as a `tf` frame (e.g. `aruco_ros` / `charuco`). Confirm the marker
   frame appears in `ros2 run tf2_tools view_frames`.
2. MoveIt running (`just moveit-dance` brings up move_group) — easy_handeye2 uses it
   to drive the arm through poses.

## Run (eye-in-hand example — gripper cam)
```bash
ros2 launch easy_handeye2 calibrate.launch.py \
  calibration_type:=eye_in_hand \
  name:=left_gripper_camera \
  robot_base_frame:=world \
  robot_effector_frame:=openarm_left_ee_base_link \
  tracking_base_frame:=left_gripper_camera_optical_frame \
  tracking_marker_frame:=aruco_marker
```
Collect **15–20 poses** spread in orientation + position (each must see the marker),
click **compute**, then **save**. Torso cam: `calibration_type:=eye_to_hand`,
target on a gripper, camera frame fixed.

> **Solver:** prefer **PARK** or **ANDREFF**, not TSAI. Our `sim_verify_handeye.py`
> showed TSAI off by ~33 mm even on noise-free data, while PARK/ANDREFF recovered the
> transform exactly. Run `python3 cameras/sim_verify_handeye.py` and
> `sim_verify_intrinsics.py` to confirm the calibration pipeline recovers known
> ground truth before trusting it on real data.

## ⚠️ Rolling shutter (the RGB torso cam)
A global-shutter cam can be captured while moving; a **rolling-shutter** cam skews
during motion and corrupts the PnP. For the RGB torso cam: **move → stop → settle
(~0.5 s) → capture** at each pose. (Test which it is: wave something fast across the
view — leaning vertical edges = rolling shutter.)

## Output → into the robot
easy_handeye2 saves the transform. Paste each result's xyz/rpy into
`cameras/openarm-cameras.xacro` and `xacro:include` it from the robot description,
so `tf` knows where every camera is — which is what perception/grasping needs.
