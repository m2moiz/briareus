# OpenArm zero-position calibration (official)

Uses OpenArm's **own** calibration tools (from `openarm-can-utils`), not a custom
routine. Run on the Linux machine wired to the arm, after `scripts/provision-hardware.sh`.

> Calibration sets each motor's **zero** to match the URDF. If skipped or wrong,
> every scripted/MoveIt pose is offset and unsafe. OpenArm spec: at the reference
> pose every joint must read within **±0.05 rad** of zero.

## One command

```bash
bash scripts/calibrate-hardware.sh
```

It runs, in order:

| Step | Tool | What it does |
|---|---|---|
| 1 | `openarm-can-configure-socketcan-4-arms can0 -fd` (and `can1`) | Bring up both CAN-FD buses |
| 2 | `openarm-can-cli -i can0 discover` (and `can1`) | Confirm every motor is on the bus |
| 3 | `openarm-can-motor-sampling-check --all 500 can0 -fd` | Motor health / sampling check |
| 4 | `openarm-can-zero-position-calibration --canport can0 --arm-side right_arm` (and `can1`/`left_arm`) | Set zero, per arm |
| 5 | launch + `ros2 topic echo /joint_states` | Verify ±0.05 rad at reference |

## The one manual step (can't be automated)

Before step 4 the script pauses and asks you to **physically place the arm at its
reference pose** — the assembly "zero" pose where all joints should read 0. That
position *defines* zero, so a human must set it; everything else is automatic.

## Defaults & overrides

- Bimanual buses: `right_arm=can0`, `left_arm=can1` (OpenArm defaults).
- Override: `RIGHT_CAN=can0 LEFT_CAN=can1 bash scripts/calibrate-hardware.sh`.

## When to re-run

Only after a motor is reseated, replaced, or its ID changed. Otherwise the zero
persists in the motor.

## Verify it worked

```bash
ros2 launch openarm_bringup openarm.bimanual.launch.py use_fake_hardware:=false
ros2 topic echo /joint_states     # at the reference pose, every position ~0.00 (±0.05)
```
