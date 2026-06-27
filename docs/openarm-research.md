# OpenArm — Complete Research Briefing

> Compiled for a hackathon build with physical OpenArm access. Every fact below is
> tagged by source confidence: **[verified]** = I read the primary source directly;
> **[reported]** = surfaced by research agents but not independently confirmed.
> Date compiled: 2026-06-27.

---

## 0. Read this first (the things that will bite you)

- **You linked `docs.openarm.dev/1.0/`, but 1.0 is deprecated.** The docs state 1.0 is no longer
  maintained; **2.0 is current**. Use `https://docs.openarm.dev/`. **[verified]**
- **Linux only.** The CAN-bus USB adapter has no macOS drivers and is untested on Windows.
  Have an Ubuntu box ready (22.04 is safest for the ROS 2 path). **[verified]**
- **There are THREE software entry points**, not one: **LeRobot**, **dora-rs**, and **ROS 2**.
  They all sit on the same `openarm_can` library. Pick one early. **[verified]**
- The arm's **8th axis is the gripper** — it's a **7-DOF** arm. A third-party wiki claiming
  "8-DOF / ~1 kg payload" is **wrong**; ignore it. **[verified]**

---

## 1. What OpenArm is  [verified]

| Spec | Value |
|---|---|
| Type | Open-source **7-DOF** humanoid arm + gripper |
| Reach | **633 mm** |
| Payload | **6.0 kg peak / 4.1 kg nominal** per arm |
| Joints | **QDD backdrivable** Damiao motors (DM8009 / DM4340 / DM4310), high compliance |
| Control bus | **CAN / CAN-FD** over Linux **SocketCAN** (1 Mbps nominal, 5 Mbps data) |
| Scale | sized for a ~160–165 cm human |
| Price | **$6,500** for a full bimanual (two-arm) system; DIY or assembled |
| Maker | **Enactic, Inc.** |
| License | **Apache-2.0** (software), **CERN-OHL-S-2.0** (hardware) |

**Why it's built this way:** quasi-direct-drive joints let the arm be pushed by hand and "feel"
external force from motor current alone (no force/torque sensor). That enables **bilateral
teleoperation** (you feel what the robot touches) and safe **contact-rich** tasks — the whole point
of the platform is high-fidelity imitation-learning data collection.

---

## 2. Complete GitHub repo map  [verified — org:enactic, 2026-06-27]

The `enactic` org has **~47 repos**. Main repo `enactic/openarm`: **2,648 ⭐ / 291 forks**.
Organized by what you'd actually use:

### Core stack
| Repo | ⭐ | What it is |
|---|---|---|
| **openarm** | 2648 | Umbrella / landing repo, docs hub |
| **openarm_hardware** | 473 | CAD for manufacturing (CERN-OHL-S-2.0) |
| **openarm_ros2** | 102 | ROS 2 packages: `ros2_control`, MoveIt 2, bringup, **bimanual** moveit config |
| **openarm_isaac_lab** | 98 | NVIDIA Isaac Lab sim + RL training |
| **openarm_can** | 54 | **C++ CAN motor library** (+ experimental Python bindings) — the foundation |
| **openarm_mujoco** | 44 | MuJoCo model + assets |
| **openarm_teleop** | 35 | Unilateral + **bilateral** teleoperation |
| **openarm_description** | 35 | URDF / xacro (single-arm + bimanual) |
| **openarm_control** | 3 | Kinematics & dynamics |
| **openarm_driver** | 1 | High-level control API |
| **openarm_dataset** | 2 | Dataset format for recorded data |
| **openarm_ker** | 4 | **KER = Kinematic Equivalent Replica**, a lightweight *leader arm* for teleop |
| **openarm_ker_firmware** | 0 | Firmware for the KER leader arm |
| **damiao** | 2 | Damiao motor reference (EN/JP) |

### Simulation extras
- **openarm_maniskill_simulation** — ManiSkill sim
- **openarm_mujoco_hardware** — MuJoCo hardware bridge
- ⚠️ **openarm_simulation** and **openarm_isaaclab_experiment** are **ARCHIVED** — don't build on them.

### dora-rs ecosystem (~25 repos, the most actively developed surface — many updated this week)
This is the **node-based dataflow** path and is clearly where a lot of current effort goes:
- `dora-openarm` (control), `dora-openarm-ros2` (bridge to ROS2), `dora-openarm-mujoco` (sim)
- `dora-openarm-vr` — **VR teleop via Meta Quest 3**
- `dora-openarm-ker` — use the KER leader arm to drive the follower
- Data collection: `dora-openarm-data-collection`, `-data-collection-ui`, `-dataset-recorder`, `-dataset-replayer`
- Inference / policy serving: `dora-openarm-inference`, `-inference-controller`, `-local-policy-server`,
  `-docker-policy-server`, `-classifier` (task success/fail), plus many `-dummy-*` test mocks
- `dora-openarm-kinematics` (FK/IK), `dora-openarm-actions-executor`, `dora-openarm-cell-lifter`

### OpenEval (auto-evaluation framework — the "OpenArm Cell" idea)
- **openeval-runner**, **openeval-web** — standardized, reproducible task evaluation.

---

## 3. The three software paths — pick one

| Path | Best for | Entry point |
|---|---|---|
| **LeRobot** (HuggingFace) | Fastest demo: teleop → record → train an IL policy (ACT / SmolVLA / π0 / Diffusion) | `huggingface.co/docs/lerobot/openarm` **[verified]** |
| **dora-rs** | Modular perception + control dataflows, VR teleop, policy serving, eval | the `dora-openarm-*` repos **[verified they exist]** |
| **ROS 2** | Motion planning (MoveIt 2), integrating with an existing ROS stack | `enactic/openarm_ros2` **[verified]** |

> At the GOSIM hackathon (§6) the two **blessed stacks were dora-rs (+ RealSense) and LeRobot (+ 3 cameras)**.
> If that's your event, start with one of those two.

---

## 4. Setup / getting started

### 4a. CAN library via APT PPA (foundation for everything)  [verified — openarm_can README]
Ubuntu 22.04 / 24.04:
```bash
sudo add-apt-repository -y ppa:openarm/main
sudo apt install -y libopenarm-can-dev openarm-can-utils

# bring up the CAN interface
openarm-can-configure-socketcan can0          # CAN 2.0 (1 Mbps)
openarm-can-configure-socketcan can0 -fd      # CAN-FD (5 Mbps data)
```
- C++ is the primary API (`include/openarm/`). Python bindings exist but are flagged
  **"⚠️ UNSTABLE API — may break between versions."**

### 4b. LeRobot path (fastest to an autonomous demo)  [verified — lerobot/openarm docs]
```bash
# install Damiao motor support into LeRobot
pip install -e ".[damiao]"

# CAN interfaces (can0 = follower, can1 = leader)
lerobot-setup-can --mode=setup --interfaces=can0,can1
lerobot-setup-can --mode=test  --interfaces=can0,can1

# calibrate follower + leader
lerobot-calibrate --robot.type=openarm_follower --robot.port=can0 --robot.side=right --robot.id=my_follower
lerobot-calibrate --teleop.type=openarm_leader  --teleop.port=can1 --teleop.id=my_leader

# teleoperate (leader drives follower)
lerobot-teleoperate \
  --robot.type=openarm_follower --robot.port=can0 --robot.side=right --robot.id=my_follower \
  --teleop.type=openarm_leader  --teleop.port=can1 --teleop.id=my_leader

# record a dataset for training
lerobot-record \
  --robot.type=openarm_follower --robot.port=can0 --robot.side=right --robot.id=my_follower \
  --teleop.type=openarm_leader  --teleop.port=can1 --teleop.id=my_leader \
  --repo-id=YOUR_HF_USERNAME/my_openarm_dataset --fps=30 --num-episodes=10
```
- **Bimanual:** classes `bi_openarm_follower` / `bi_openarm_leader`; followers on `can0`/`can1`,
  leaders on `can2`/`can3` (via `--robot.left_arm_config.port=...` etc.).
- **Programmatic (no leader arm):**
  ```python
  from lerobot.robots.openarm_follower import OpenArmFollower, OpenArmFollowerConfig
  f = OpenArmFollower(OpenArmFollowerConfig(port="can0", side="right", id="my_follower"))
  f.connect()
  f.send_action({f"joint_{i}.pos": 0.0 for i in range(1,8)} | {"gripper.pos": 0.0})
  f.disconnect()
  ```
- **Key config flags:** `use_can_fd=True`, `can_bitrate=1_000_000`, `can_data_bitrate=5_000_000`,
  `max_relative_target` (per-step safety clamp — **set this while testing!**), per-joint `position_kp`/`kd`.
- **Motor map (default IDs):** j1–2 = DM8009 (shoulder), j3–4 = DM4340 (elbow), j5–7 + gripper = DM4310 (wrist);
  send IDs `0x01–0x08`, recv `0x11–0x18`.
- **If motors are silent:** check power → CAN-H/CAN-L/GND wiring → `lerobot-setup-can --mode=test` → `ip link show can0`.

### 4c. ROS 2 path  [reported — confirm distro on the repo]
```bash
git clone https://github.com/enactic/openarm_ros2
ros2 launch openarm_ros2 openarm.launch.py use_fake_hardware:=true   # sim without hardware
```
- Confirmed: MoveIt 2 + `ros2_control` + bimanual moveit config exist in the repo. Exact ROS 2 distro /
  Ubuntu version: **[reported]** Ubuntu 22.04 + Humble — verify on `docs.openarm.dev/software/ros2/install`.

---

## 5. "Skills" / policies / imitation learning

There is **no library of pre-trained, drop-in task policies** ("pick up the cup"). What exists is the
**full IL pipeline** to *make* one:

- **Via LeRobot:** record teleop demos → fine-tune **ACT, Diffusion Policy, SmolVLA, π0** → deploy. **[verified path]**
- **Via dora-rs:** dedicated policy-server + inference + task-classifier nodes for online deployment. **[verified repos exist]**
- **For RL / sim-to-real:** `openarm_isaac_lab` (Isaac Lab), `openarm_mujoco`, `openarm_maniskill_simulation`. **[verified repos exist]**
- **Eval:** OpenEval (`openeval-runner` / `openeval-web`) for reproducible scoring. **[verified repos exist]**
- **[reported, low confidence]** A secondary wiki claims OpenVLA support and `<50 ms` teleop latency — that
  same wiki had the DOF/payload wrong, so confirm before relying on it.

**Hackathon recommendation:** record ~10–50 demos of your target task and fine-tune **ACT** (simplest,
robust) or **SmolVLA** (language-conditioned). Shortest line from "we have an arm" to "it does a thing."

---

## 6. The hackathon context  [verified — GOSIM Paris 2026 page]

**GOSIM Paris 2026 Robotics / Physical-AI Hackathon (Unaite × GOSIM)** — May 5–6 2026, **Station F, Paris**,
teams of 3–5 (~50 people). **Each team gets one OpenArm (7-DoF, 633 mm reach) + a teleop kit.**
- **Tasks:** grasping, pick-and-place, **pouring liquids, bin picking, cloth folding, board assembly, object hand-over**.
- **Stacks offered:** **dora-rs + Intel RealSense** (3D perception) OR **LeRobot + 3 cameras** (multi-view teleop).
  Platform also supports ROS 2, MuJoCo, Isaac Lab.
- A **simulation environment is provided pre-event**, and **remote physical robot access** is available after you
  validate in sim. (If your event is different, the value here is the realistic task list + the two recommended stacks.)

---

## 7. Documentation map (docs.openarm.dev, v2.0)

Overview · Getting Started (Project Overview, **Safety Guide**, Contribution Guide) · Hardware (BOM, 3D printing,
assembly, wiring) · Software (`openarm_can`, ROS 2/MoveIt, URDF, Isaac Lab + MuJoCo) · Teleop (Setup,
**Unilateral**, **Bilateral**, **VR**) · Simulation · FAQ · Purchase.

> Note: the `/software/` page is JavaScript-rendered, so automated fetchers see it as empty — read it in a browser.

---

## 8. Community & links
- **Discord:** docs link `discord.gg/tpnKxHuJY3`; GitHub README links `discord.gg/FsZaZ4z3We` (two invites in the wild).
- **GitHub:** `github.com/enactic` · **Site:** `openarm.dev` · **X:** `@enactic_ai` · **Docs:** `docs.openarm.dev`.

---

## 9. Sources & verification notes
**Primary (read directly):** `docs.openarm.dev` (+ `/hardware/`), `github.com/enactic/openarm`,
`/openarm_can`, `/openarm_ros2`, the full `enactic` org repo list (GitHub API),
`huggingface.co/docs/lerobot/openarm`, `openarm.dev`, GOSIM Paris 2026 hackathon page.
**Secondary (partly inaccurate — got DOF & payload wrong):** `roboticscenter.ai`.

**On the deep-research run:** the workflow's auto-conclusion ("all 25 claims refuted") was a false
negative — its verification phase was rate-limited by the API and every vote *abstained* (scored as
"killed"). Search + fetch succeeded (8 sources, 38 claims); all load-bearing facts above were
re-verified by direct fetches, which is why several first-pass items got corrected here
(repo count 9 → ~47; PPA packages; `openarm_simulation` is archived; DOF/payload conflicts resolved).

---

## 10. ROS 2 Route — verified build + macOS/Apple-Silicon plan

> All of this was read directly from the live docs (rendered via a real browser, since the pages are
> JavaScript-rendered) and the repo's authoritative build files (`Dockerfile`, `package.xml`, `.repos`,
> bringup README). Docs last updated 2026-06-26. **[verified]**

### Platform reality
- **OpenArm hardware is Linux-only** — the CAN-bus USB adapter has **no macOS driver**. You cannot drive
  the real arm from a Mac, a Mac VM, or Docker-on-Mac (SocketCAN is a Linux-kernel subsystem; USB-CAN
  passthrough into a Mac-hosted VM is unreliable). **[verified]**
- **ROS 2 on macOS is not viable** (Tier-3 source build; Humble dropped Mac). Don't.
- **Plan:** develop the whole stack in an **Ubuntu 22.04 ARM64 VM** with `use_fake_hardware:=true`
  (MoveIt, RViz, perception — everything but real CAN). Drive the **physical arm from a native Linux
  host** (your own, or the hackathon's provided machine + remote robot access — confirm with organizers).

### Verified target
- **ROS 2 Humble** (Jazzy also supported; Humble recommended) → **Ubuntu 22.04 (Jammy)**.
- Humble ships **native arm64 debs**, so an M-series Mac runs ARM Ubuntu + ARM ROS with **no emulation**.

### Exact apt dependencies (canonical install page)
```
ros-humble-desktop ros-dev-tools
# ros2_control:
ros-humble-controller-manager ros-humble-gripper-controllers ros-humble-hardware-interface
ros-humble-joint-state-broadcaster ros-humble-joint-trajectory-controller
# MoveIt 2:
ros-humble-forward-command-controller ros-humble-moveit-configs-utils ros-humble-moveit-planners
ros-humble-moveit-ros-move-group ros-humble-moveit-ros-visualization ros-humble-moveit-simple-controller-manager
```

### Build
```bash
git clone https://github.com/enactic/openarm_ros2 ~/ros2_ws/src/openarm_ros2
# pull openarm_can source (SKIP if openarm_can is installed system-wide via PPA, or for mock-only):
(cd ~/ros2_ws/src && vcs import < ./openarm_ros2/openarm.repos)
cd ~/ros2_ws && colcon build              # mock-only: add  --packages-ignore openarm_hardware
source ~/ros2_ws/install/setup.bash
```

### Run / test (verified commands)
```bash
ros2 launch openarm_bringup openarm.launch.py arm_type:=v10 use_fake_hardware:=true      # no robot
ros2 launch openarm_bringup openarm.bimanual.launch.py arm_type:=v10 use_fake_hardware:=true
ros2 launch openarm_bimanual_moveit_config demo.launch.py                                 # MoveIt 2
ros2 action list
# real arm (on Linux host): use_fake_hardware:=false can_interface:=can0
```
- Params: `arm_type` (def `v10`), `use_fake_hardware` (def `false`), `can_interface` (`can0`),
  `robot_controller` (`joint_trajectory_controller` | `forward_position_controller`).
- ⚠️ **Param-name discrepancy:** docs say `use_fake_hardware:=true`; the repo's `openarm_bringup/README.md`
  says `hardware_type:=mock|mujoco|real`. Run `ros2 launch openarm_bringup openarm.launch.py --show-args`
  on your clone to see which it actually exposes.
- Joint test: `ros2 action send_goal /joint_trajectory_controller/follow_joint_trajectory`
  `control_msgs/action/FollowJointTrajectory` with joints `openarm_joint1..7`.
- **Control gains** are deliberately low (arm may not reach high angles); edit
  `~/ros2_ws/src/openarm_description/config/arm/v10/control_gains.yaml` then `colcon build`. Raise gradually.

### ⚠️ Maturity caveat (matters for a hackathon)
The docs state in their own words that the **hardware bridging is "currently being updated and may be
unstable"** (gripper especially), and **MoveIt 2 integration is "under active development."** Validate
everything in `use_fake_hardware:=true` first; budget buffer for real-hardware bring-up; keep the
LeRobot/dora path as a live-demo fallback.

### Setup script
`setup-openarm-ros2-vm.sh` (in this folder) provisions the mock-dev stack end-to-end inside a fresh
Ubuntu 22.04 VM (idempotent; skips CAN/hardware). It prints the real-hardware ("PART C") steps for the
Linux host at the end. Verified statically (`bash -n` + shellcheck); must be run inside the Ubuntu VM.
