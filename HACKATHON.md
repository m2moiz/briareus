# briareus — Paris Builds 2026 (by Unaite)

**Event:** **Paris Builds** (a hackathon by **Unaite**) · Paris · **June 27–28, 2026** (36-hour build)
**What I built:** briareus — a bimanual [OpenArm](https://github.com/enactic/openarm) robot (two 7-DOF arms with grippers), driven entirely **in simulation on macOS** (no hardware required).
**Team:** _TODO solo or teammates_
**Result:** _TODO placement (no public winners page found)_
**Repo:** https://github.com/m2moiz/briareus
**Demo:** `just` task targets wrap the VM + ROS 2 launches; Foxglove bridge for visualization

## What it does
- Two 7-DOF OpenArm arms + grippers in sim
- Perception kit for three UVC cameras (one per gripper, eye-in-hand + one overhead)
- Motion demos: wiggle test, scripted poses, a collision-aware MoveIt "Macarena," and a beat-synced Macarena
- Calibration runbooks + no-hardware regression suites checking against known ground truth
- Stack: macOS host ↔ Lima VM "openarm" (Ubuntu 22.04) running ROS 2 + MoveIt; `justfile` wrappers; Foxglove

## Public event facts (researched 2026-06-29, sourced)
- **"uniate" = Unaite** — "the student federation uniting France's leading AI institutions" (unaite.fr).
- **Dates / venue:** Sat **June 27** 09:00 → Sun **June 28** 18:30, 2026 (36h) · **Stephenson Harwood, 48 Rue Cambon, 75001 Paris.**
- **Theme:** a 36-hour startup-build hackathon — "stop talking about your startup and start building it," with a shot at a **Y Combinator interview**.
- **Three tracks:** (1) Software for Agents; (2) **Robotics — "access to OpenArm and dedicated compute"** (← mine); (3) "The Next Big DecaCorn" (open).
- **Partner:** **Y Combinator** (winning teams get a YC interview; YC-alumni mentors in-room). Flyer sponsors: **Botifull, Anthropic, QRT (Qube Research & Technologies), Hugging Face.**
- **Hardware:** OpenArm (open-source 7-DoF arm by **Enactic**; bimanual system ~$6,500). Teams of 3–5.
- **Prize:** an interview with **Y Combinator** (no cash prize stated).
- **Sources:** https://luma.com/8ucy347o · unaite.fr · github.com/enactic/openarm.

## Notes
- Named "briareus" after the hundred-handed giant of Greek myth (bimanual robot).
- ⚠️ There is ALSO a separate **GOSIM × Unaite Robotics Hackathon** (May 5–6, 2026, Station F) where teams got a *physical* OpenArm — **this project (briareus) is Paris Builds, June 27–28**, not that one.
- _TODO (yours):_ team, placement, demo video.
