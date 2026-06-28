# Getting started

This guide takes a fresh machine to a running OpenArm demo in simulation, then on to the camera calibration kit. Everything here is sim-only with fake hardware: the ROS 2 stack runs inside a Lima virtual machine, and your Mac runs the task runner and the viewers. Driving the physical arm needs a native Linux host with a CAN bus and is covered in `HARDWARE.md` and `CALIBRATION.md`.

## 1. Host prerequisites (macOS)

Install three things on the Mac:

- Lima, which provides `limactl` to create and run the Linux VM: `brew install lima`
- just, the command runner that reads the `justfile`: `brew install just`
- Foxglove, the desktop app for 3D visualization. It connects to the VM's WebSocket bridge at `ws://localhost:8765`. Install it from foxglove.dev.

Apple Silicon Macs run the VM natively on arm64 with no emulation. ROS 2 Humble, ros2_control, and MoveIt 2 all run inside the VM, so nothing else needs installing on the host. The interactive MoveIt and RViz targets use an in-VM VNC server reached through macOS Screen Sharing, so you do not need XQuartz or X11 forwarding.

## 2. Create and enter the VM

The scripts target a Lima VM named `openarm`. Create one running Ubuntu 22.04 with the spec this project was built and verified against (4 CPU, 8 GiB RAM, 64 GiB disk):

```bash
limactl start --name=openarm --cpus=4 --memory=8 --disk=64 template://ubuntu-22.04
```

Day-to-day VM management:

```bash
limactl start openarm     # boot it     (also: just vm-up)
limactl stop openarm      # shut it down (also: just vm-down)
limactl shell openarm     # shell inside the VM (also: just shell)
```

## 3. Provision ROS 2 and build the workspace

With the VM running, provision ROS 2 Humble and build the OpenArm packages. `scripts/provision-ros2.sh` runs inside the guest, so feed it over stdin:

```bash
limactl shell openarm bash -s < scripts/provision-ros2.sh
```

The script is idempotent and safe to re-run. It runs six steps: sets the locale, adds the ROS 2 apt repository, installs `ros-humble-desktop` plus the ros2_control and MoveIt 2 dependencies, clones `enactic/openarm_ros2` into `~/ros2_ws/src`, runs `colcon build --symlink-install --packages-ignore openarm_hardware`, and appends the two `source` lines to `~/.bashrc`. The CAN-based `openarm_hardware` interface is deliberately ignored, so the sim never needs CAN. The long step is the ROS 2 desktop install.

When it finishes it lists the built packages. You should see `openarm`, `openarm_bringup`, `openarm_bimanual_moveit_config`, and `openarm_description`.

`scripts/build-ros2.sh` is the build-only re-run, for when the apt packages are already installed and you just need to rebuild the workspace.

Every command run inside the VM sources both setup files first:

```bash
limactl shell openarm bash -lc 'source /opt/ros/humble/setup.bash; source ~/ros2_ws/install/setup.bash; <cmd>'
```

Provisioning adds those two `source` lines to `~/.bashrc`, so an interactive `limactl shell openarm` already has them. One quirk: ROS 2's `setup.bash` references unbound variables, so scripts that source it avoid `set -u` (strict mode).

## 4. Run the headline demo

From the repo root on the Mac:

```bash
just demo
```

This runs `scripts/openarm-demo.sh`, which starts the `openarm` VM if it is not already running, pushes the latest `scripts/wiggle.py` into the VM, opens the Foxglove app, then launches the full sim stack inside the VM: bimanual bringup with fake hardware, the wiggle motion node, and the Foxglove bridge. The VM-side commands are:

```text
ros2 launch openarm_bringup openarm.bimanual.launch.py use_fake_hardware:=true
python3 ~/wiggle.py
ros2 run foxglove_bridge foxglove_bridge --ros-args -p port:=8765 -p address:=0.0.0.0
```

When the terminal prints `CONNECT Foxglove now`, switch to Foxglove, choose Open Connection, enter `ws://localhost:8765`, and add a 3D panel. Both arms wiggle live, running counter-phase. Press Ctrl-C in the terminal to stop everything in the VM; the VM itself stays up.

`scripts/wiggle.py` publishes slow, phase-shifted sinusoidal `JointTrajectory` commands to both arm controllers. The defaults are amplitude 0.3 rad, period 6 s, rate 20 Hz, all exposed as ROS parameters.

## 5. The launch targets

Run `just` with no argument to list every target. The full set:

| Target | What it does |
|---|---|
| `just demo` | VM + bimanual bringup (fake hardware) + wiggle motion + Foxglove bridge, opens Foxglove. The headline demo. |
| `just foxglove` | Robot bringup + Foxglove bridge only, no auto-wiggle (`scripts/openarm-foxglove.sh`). |
| `just wiggle` | Run `~/wiggle.py` against an already-running robot (start one first, e.g. `just foxglove`). |
| `just moveit` | Interactive MoveIt 2 in RViz via in-VM VNC. Connect with `open vnc://localhost:5901` (password: `openarm`). |
| `just rviz` | Bare RViz2 via in-VM VNC (same connection and password). |
| `just moveit-dance` | Collision-aware MoveIt Macarena; each beat is planned and collision-checked (watch via VNC). |
| `just macarena-music` | Beat-synced Macarena to a 103 BPM click track; audio plays on the Mac, the arm moves in sim. |
| `just drums` | Bimanual drum beat (alternating toms) with drumsticks rendered in the grippers, plus a synced drum loop on the Mac. Watch in Foxglove. |
| `just stop` | Stop all ROS processes in the VM; the VM keeps running (`scripts/stop.sh`). |
| `just shell` | Open a shell inside the VM. |
| `just vm-up` / `just vm-down` | Start / stop the VM itself. |
| `just status` | Show the VM state and whether the ROS control node is running. |

The arm brings up five controllers: `joint_state_broadcaster`, `left_joint_trajectory_controller`, `right_joint_trajectory_controller`, `left_gripper_controller`, and `right_gripper_controller`.

## 6. Viewing the arm

There are two viewers, picked by which target you run.

Foxglove gives smooth 3D and is used by `just demo` and `just foxglove`. The VM runs `foxglove_bridge` on port 8765. In the Foxglove desktop app, choose Open Connection, enter `ws://localhost:8765`, and add a 3D panel.

The in-VM VNC viewer with RViz or MoveIt is used by `just moveit`, `just rviz`, `just moveit-dance`, and `just macarena-music`. `scripts/openarm-vnc.sh` runs a virtual X server (Xvnc) on display `:1` inside the VM and renders RViz there with software Mesa (`LIBGL_ALWAYS_SOFTWARE=1`), so only finished pixels travel to the Mac. This avoids the indirect-GLX failures you hit forwarding RViz's OpenGL context over X11. Connect with macOS Screen Sharing:

```bash
open vnc://localhost:5901      # password: openarm
```

The VNC tooling installs inside the VM once, on first use of a VNC target. The script sets the fixed password `openarm`, clears any stale RViz, `move_group`, or controller processes, then launches either `rviz2` or `ros2 launch openarm_bimanual_moveit_config demo.launch.py`.

If MoveIt's translucent planning overlays clutter the view, run `scripts/rviz-hide-ghosts.sh` inside the VM once. It edits the `moveit.rviz` config to turn off the Planned Path replay, the draggable goal-state ghost, and Loop Animation while keeping the solid Scene Robot. Then relaunch RViz.

## 7. The motion demos

All of these run against the fake-hardware sim. With the sim up, run the Python nodes inside the VM (the `just` targets handle bringup for you).

Wiggle is the quickest live-motion check:

```bash
just demo       # VM up + bringup + wiggle + Foxglove bridge, opens Foxglove; Ctrl-C stops everything
just foxglove   # robot + Foxglove bridge only, no auto-wiggle
just wiggle     # wiggle an already-running robot
```

The scripted bimanual sequence, `scripts/bimanual_sequence.py`, reads named poses (`home`, `hands_up`, and so on) straight from the MoveIt SRDF and commands the trajectory controllers directly, with no collision checking. Run it inside the VM with the sim already up:

```bash
python3 bimanual_sequence.py            # full choreography: home, hands_up, wrist wave, home
python3 bimanual_sequence.py hands_up   # strike one named pose and hold
```

The raw-trajectory Macarena, `scripts/macarena.py`, maps the 16-count routine onto expressive joint poses and drives the trajectory controllers directly. The right arm is the left arm mirrored.

```bash
python3 macarena.py
```

The collision-aware Macarena is the safe version, exposed as a target:

```bash
just moveit-dance
```

`scripts/moveit-dance.sh` copies `moveit_motion.py` and `macarena_moveit.py` into the VM, brings up `ros2 launch openarm_bimanual_moveit_config demo.launch.py` on the VNC display if it is not already running, and waits for the "You can start planning now" line. Under CPU load a trajectory controller can lose the spawn race, so the script re-spawns any of the five expected controllers that did not come up active before running the dance. Every beat is planned and executed through MoveIt's `/move_action`, with self-collision checking against the URDF geometry and the SRDF allowed-collision matrix, velocity scaling `vel_scale=0.2`, 10 planning attempts, and a 5 s planning-time budget. A beat that would self-collide or is unreachable is reported and skipped rather than driven blindly, and the run prints how many beats executed versus skipped. Watch it over VNC at `vnc://localhost:5901`.

The beat-synced Macarena plays the dance against a 103 BPM click track. The click plays on the Mac through `afplay`; the arm dances in the VM. They start together so the count-ins line up.

```bash
just macarena-music
```

`scripts/macarena-music.sh` generates the click track on first run via `scripts/make-click-track.py` (into `assets/macarena_click_103bpm.wav`), copies `macarena_synced.py` into the VM, ensures `move_group` and all five controllers are up, then starts the dance and the audio together. `scripts/macarena_synced.py` builds one timed `JointTrajectory` per arm with waypoints stamped at exact beat times and lets the controller replay them on those timestamps, so each move lands on its beat. Live MoveIt planning is too slow to hit the 0.58 s beats, which is why these already-validated poses are played back on a timed schedule instead. The BPM is an optional argument and defaults to 103.

The drum beat plays a bimanual groove with drumsticks held in the grippers:

```bash
just drums            # 90 BPM, 4 bars
just drums 100 8      # BPM and bar count are optional arguments
```

`scripts/drums.sh` brings up fake hardware through `scripts/drums.launch.py`, which adds two drumstick links to the robot description (one fixed to each gripper's `ee_base_link`, pointing out along the grasp axis) and starts a Foxglove bridge. `scripts/drumbeat.py` plays an alternating-tom pattern (the arms trade strikes left-right on an 8th-note pulse) as timed trajectories that land on the beat grid, the same approach as the synced Macarena. `scripts/make-drum-loop.py` synthesizes a matching two-tom loop that plays on the Mac in time with the strikes. Because the sticks are rendered, watch this one in Foxglove (Open Connection, `ws://localhost:8765`, add a 3D panel) rather than RViz.

A shared helper, `scripts/safe_motion.py`, can pace trajectories to calibrated per-joint safe velocities read from `motion_limits.yaml`, falling back to slow defaults when no calibration file exists yet.

## 8. Manual launch (inside the VM)

To bring the robot up by hand without the wrapper scripts:

```bash
limactl shell openarm
ros2 launch openarm_bringup openarm.bimanual.launch.py use_fake_hardware:=true
# in another shell, inspect the running graph:
ros2 node list
ros2 topic echo /joint_states --once
```

A few facts hold for this workspace: the launch argument is `use_fake_hardware:=true` (the default is already `true`), only the bimanual launch file `openarm.bimanual.launch.py` ships, and the build ignores `openarm_hardware` so the sim never needs CAN.

## 9. Motion-limit calibration (runs in sim, tunes on hardware)

`scripts/calibrate.py` is the startup calibration. Run it once with the sim (or hardware) up, before the motion scripts:

```bash
python3 calibrate.py            # full slow calibration -> motion_limits.yaml
python3 calibrate.py --check    # preflight only, no motion
```

It runs a preflight that checks every joint is at home within ±0.05 rad, a gravity probe (static effort at home), and a slow ±0.1 rad articulation sweep per joint to derive a safe max velocity, then writes `motion_limits.yaml`. On the mock sim there is no gravity, effort, or tracking error, so the file is written with conservative defaults marked `measured: false` and a global `speed_scale` of 0.20. The real gravity and tracking tuning (`measured: true`, `speed_scale` 0.25) only happens on hardware. If a joint reads far from zero during preflight, the motor zero is wrong; see `CALIBRATION.md`.

## 10. Stopping and status

```bash
just stop       # kill all ROS processes in the VM (the VM stays up)
just status     # show VM state and whether ROS is running
just shell      # open a shell inside the VM
just vm-up      # start the VM
just vm-down    # stop the VM
```

`just stop` runs `scripts/stop.sh`, which kills the ROS processes (`ros2_control_node`, `foxglove_bridge`, `robot_state_publisher`, `wiggle.py`, the bringup launch, the spawners) and confirms they stopped. `just demo` also cleans these up on Ctrl-C.

## 11. Camera calibration and the sim-verify suite

The camera kit lives under `cameras/` and is documented in full in `cameras/README.md`. It calibrates the three UVC cameras (torso plus one per gripper) so each camera's intrinsics and extrinsics are known and published in `tf`. The calibration steps themselves run on the Linux box wired to the cameras and the arm; the regression suite runs against a sourced ROS 2 with no hardware attached.

### Order of operations (on the real camera rig)

1. Install the toolchain: `bash cameras/provision-cameras.sh` (apt drivers and calibration packages, plus `easy_handeye2` built from source).
2. Pin the cameras with udev: `bash cameras/discover-cameras.sh`, copy each USB port path into the `FILL-*` placeholders in `cameras/99-openarm-cameras.rules`, install to `/etc/udev/rules.d/`, reload, and confirm `/dev/cam_*`.
3. Calibrate intrinsics, one camera at a time. See `cameras/calibrate-intrinsics.md`. Results go to `cameras/calib/<name>.yaml`.
4. Stream with calibration loaded: `ros2 launch cameras/cameras.launch.py`.
5. Calibrate extrinsics (hand-eye). See `cameras/calibrate-handeye.md` (eye-in-hand for the grippers, eye-to-hand for the torso).
6. Bring the result into the robot: paste each calibrated transform into `cameras/openarm-cameras.xacro` and include it from the robot description.

### Running the sim-verify regression suite

The `sim_verify_*.py` scripts run with no cameras attached and check the pipeline, wiring, and math against known ground truth. Run each with a sourced ROS 2 in the dev VM, for example:

```bash
limactl shell openarm bash -lc 'source /opt/ros/humble/setup.bash; \
  source ~/ros2_ws/install/setup.bash; \
  cd <repo>/cameras && python3 sim_verify_intrinsics.py'
```

| Test | What it verifies | Needs root v4l2loopback setup |
|---|---|---|
| `sim_verify_intrinsics.py` | `calibrateCameraCharuco` recovers a known camera matrix K and distortion D | no |
| `sim_verify_detection.py` | The real detector finds a rendered ChArUco board across warped poses | no |
| `sim_verify_charuco_engine.py` | `camera_calibration.MonoCalibrator` accumulates ChArUco samples with coverage spread | no |
| `sim_verify_handeye.py` | `cv2.calibrateHandEye` (PARK) recovers a known gripper-to-camera transform | no |
| `sim_verify_handeye_launch.py` | `easy_handeye2`'s `calibrate.launch.py` wires the `eye_in_hand` config | no |
| `sim_verify_camerainfo.py` | `camera_info_url` round-trips the exact K and D onto the `camera_info` topic | no |
| `sim_verify_v4l2_pipeline.py` | The real `v4l2_camera_node` streams `image_raw` + `camera_info` off a virtual device | yes |
| `sim_verify_calibrator.py` | The `cameracalibrator` binary detects and accumulates over a live v4l2 stream | yes |
| `sim_verify_udev.py` | `99-openarm-cameras.rules` is well-formed and declares all three symlinks | no |

The two v4l2 tests need a one-time `v4l2loopback` setup that requires root (and `xvfb` for the calibrator). The exact `modprobe` and `apt-get` commands are in each script's docstring and in `cameras/README.md`. Both scripts assert that `/dev/video10` exists and is read/write accessible before they start, and exit with a pointer to that setup if it is missing.

## 12. What is simulation vs real hardware

Everything above runs in simulation with `use_fake_hardware:=true`: no CAN bus, no physical arm. The `just demo`, `foxglove`, `wiggle`, `moveit`, `rviz`, `moveit-dance`, and `macarena-music` targets are all sim, and the camera sim-verify suite checks the calibration machinery against synthetic ground truth rather than real sensors.

Driving the physical OpenArm requires a native Linux host wired to the arm's CAN bus, the `openarm_hardware` interface, and a build that includes the CAN library. That path, plus the zero-position motor calibration and the safety checklist, is in `HARDWARE.md` and `CALIBRATION.md`. The vcan path in `HARDWARE.md` lets you validate the entire real-hardware software path on a Linux machine with no arm attached before any hardware arrives.
