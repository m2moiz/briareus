# Unaite Paris Builds — OpenArm Hackathon

Working folder for the OpenArm robotic-arm hackathon project. Holds the research,
the environment-setup scripts, and the launchers for running and visualizing the arm.

## Layout

```
uniate_paris_builds_hackathon/
├── README.md                       ← this file
├── docs/
│   └── openarm-research.md          ← full research: repos, specs, LeRobot/dora/ROS2, setup, sources
├── scripts/
│   ├── setup-openarm-ros2-vm.sh     ← ROS 2 setup for a fresh Ubuntu 22.04 VM (generic)
│   ├── provision-ros2.sh            ← what provisioned the Lima VM (ROS 2 Humble + deps)
│   ├── build-ros2.sh                ← builds openarm_ros2 (mock hardware) in the VM
│   ├── openarm-foxglove.sh          ← run the arm + Foxglove bridge (smooth, GPU viz on Mac)
│   └── openarm-gui.sh               ← X11-forwarded RViz / MoveIt (needs XQuartz)
├── logs/
│   └── provision.log                ← provisioning run log
└── config.yaml                      ← stock Dolt/beads server config (pre-existing, unrelated)
```

The scripts are self-contained (they call `limactl` and `~/.lima/openarm/...` by absolute
path), so they work from this folder.

## Environment (already set up & verified)

- **Lima VM `openarm`** — Ubuntu 22.04.5 LTS, native ARM64 (Apple Silicon, no emulation),
  4 CPU / 8 GiB / 64 GiB. Manage with `limactl start|stop|shell openarm`.
- **ROS 2 Humble** + `ros2_control` + MoveIt 2, workspace at `~/ros2_ws` *inside the VM*.
- Built packages: `openarm`, `openarm_bringup`, `openarm_bimanual_moveit_config`, `openarm_description`.
- **Foxglove** desktop app installed on the Mac → connects to `ws://localhost:8765`.

The real arm needs a **native Linux host** (CAN bus is Linux-only); this VM is the dev/sim
environment. See `docs/openarm-research.md` §10 for the full rationale.

## Running it

**Smooth visualization (recommended):**
```bash
scripts/openarm-foxglove.sh          # starts robot (fake hw) + bridge in the VM
# then: Foxglove app → Open Connection → ws://localhost:8765 → add a 3D panel
```

**Manual, inside the VM:**
```bash
limactl shell openarm
ros2 launch openarm_bringup openarm.bimanual.launch.py use_fake_hardware:=true
ros2 node list ; ros2 topic echo /joint_states --once
```

**Interactive MoveIt planning (needs XQuartz on the Mac):**
```bash
scripts/openarm-gui.sh moveit
```

## Facts verified against the running system (the docs/README were wrong)

- Launch arg is **`use_fake_hardware:=true`** (default already `true`) — not `hardware_type`.
- Default `arm_type` is **`openarm_v2.0`** (not `v10`).
- Only **`openarm.bimanual.launch.py`** ships (no single-arm `openarm.launch.py`).
- **`openarm_description`** is a *separate* repo — must be cloned into the workspace.
- ROS 2's `setup.bash` trips `set -u` (`AMENT_TRACE_SETUP_FILES` unbound) — don't use strict mode around it.

## Next steps

- Add a small joint-wiggle publisher to see motion live in Foxglove.
- Pick a hackathon idea (see `docs/openarm-research.md`) and scaffold a package.
- For the real arm: provision a Linux host with `scripts/provision-ros2.sh` + `build-ros2.sh`,
  then build *with* `openarm_hardware` and bring up the CAN interface.
