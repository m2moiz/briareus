# briareus

A bimanual [OpenArm](https://github.com/enactic/openarm_ros2) robot arm, driven in simulation on macOS. The ROS 2 software runs inside a Lima VM, and you watch the arm move on your Mac in Foxglove or RViz. Driving the physical arm is a separate path that needs a native Linux host with a CAN bus, covered in `HARDWARE.md`.

## What's in here

- A bimanual OpenArm: two 7-DOF arms with grippers (joints `openarm_left_joint1..7` and `openarm_right_joint1..7`).
- A perception kit for three UVC cameras under `cameras/`: one on each gripper (eye-in-hand) and one on the torso (eye-to-hand).
- Motion demos: a wiggle test, scripted poses, a collision-aware MoveIt Macarena, a beat-synced Macarena, and a bimanual drum beat with drumsticks held in the grippers.
- A `justfile` of short task targets that wrap the VM and the ROS 2 launches.
- Calibration runbooks and no-hardware regression suites that check the machinery against known ground truth.

## Architecture

```
macOS host                              Lima VM "openarm" (Ubuntu 22.04)
----------                              --------------------------------
just (task runner) ──limactl shell──>   ROS 2 Humble + ros2_control + MoveIt 2
Foxglove app  ──ws://localhost:8765──>  foxglove_bridge   (3D viz)
Screen Sharing ──vnc://localhost:5901─> Xvnc + RViz / MoveIt (software Mesa)
                                        workspace: ~/ros2_ws
                                        bringup: openarm_bringup
                                                 openarm.bimanual.launch.py
```

The Mac runs the task runner and the viewers. Everything ROS-related (the controllers, the planner, the robot model) runs inside the VM. On Apple Silicon the VM runs natively on arm64 with no emulation. The cameras and the CAN bus only come into play on the real-hardware path.

## Five-minute quickstart

You need three things on the Mac: Lima (`brew install lima`), just (`brew install just`), and the Foxglove desktop app from foxglove.dev.

```bash
# 1. Create the VM (one time), 4 CPU / 8 GiB / 64 GiB to match the tested spec
limactl start --name=openarm --cpus=4 --memory=8 --disk=64 template://ubuntu-22.04

# 2. Provision ROS 2 Humble and build the workspace (one time; the apt step is long)
limactl shell openarm bash -s < scripts/provision-ros2.sh

# 3. Launch the demo: VM + bimanual bringup (fake hardware) + wiggle + Foxglove bridge
just demo
```

When the terminal prints `CONNECT Foxglove now`, switch to Foxglove, choose Open Connection, enter `ws://localhost:8765`, and add a 3D panel. The arm loads from `/robot_description` and both arms wiggle live. Press Ctrl-C in the terminal to stop everything inside the VM; the VM stays up.

Run `just` with no argument to list every target. The full step-by-step guide, including the camera calibration and the regression suites, is in `docs/GETTING-STARTED.md`.

## Repo map

| Path | What it covers |
|---|---|
| `docs/GETTING-STARTED.md` | Full setup and run guide: prerequisites, VM creation, workspace build, motion demos, viewers, and the camera sim-verify suite. |
| `cameras/README.md` | Camera calibration and perception kit: intrinsics, hand-eye extrinsics, udev pinning, and the `sim_verify_*.py` regression tests. |
| `CALIBRATION.md` | Zero-position motor calibration on the real arm, using OpenArm's `openarm-can-utils` tools. Real hardware only. |
| `HARDWARE.md` | Moving from the sim VM to the physical arm: CAN provisioning, the vcan software-validation path, and the real-arm launch. |
| `justfile` | The task targets (`just demo`, `just foxglove`, `just moveit`, `just macarena-music`, `just stop`, and the rest). |
| `scripts/` | The launch wrappers and motion nodes the targets call. |

## Verified in simulation vs needs the real rig

Everything in the quickstart and in `docs/GETTING-STARTED.md` runs in simulation with `use_fake_hardware:=true`: no CAN bus, no physical arm. The mock hardware has no gravity, no effort feedback, and perfect position tracking, so the demos exercise the full motion path (controllers, trajectories, MoveIt planning) without a robot attached. The camera `sim_verify_*.py` suite checks the calibration pipeline and math against synthetic ground truth, not real sensors.

These only run on the physical OpenArm, on a native Linux host wired to the CAN bus (the USB-CAN adapter has no macOS driver):

- Zero-position motor calibration (`CALIBRATION.md`, `scripts/calibrate-hardware.sh`).
- The real-arm launch with `use_fake_hardware:=false` (`HARDWARE.md`).
- The measured half of motion-limit calibration. `scripts/calibrate.py` writes conservative `measured: false` defaults in sim; real gravity and tracking tuning happens on hardware.
- The cameras' actual intrinsics and distortion, the udev USB port mapping, the torso camera's rolling-shutter behavior, and the live hand-eye capture.

The vcan path in `HARDWARE.md` lets you validate the entire real-hardware software path (plugin load, launch parsing, CAN socket open, TX frames) on a Linux box with no arm attached, before any hardware arrives.
