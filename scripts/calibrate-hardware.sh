#!/usr/bin/env bash
# OFFICIAL OpenArm zero-position calibration (CAN / ROS 2 route).
#
# Wraps OpenArm's OWN tools from openarm-can-utils — not a custom routine:
#   openarm-can-configure-socketcan-4-arms  — bring up the CAN bus (CAN-FD)
#   openarm-can-cli discover                — confirm motors are on the bus
#   openarm-can-motor-sampling-check        — motor health check
#   openarm-can-zero-position-calibration   — set the zero pose, per arm
#
# REQUIRES the physical arm, powered and on CAN. It CANNOT run without hardware
# (the tools talk to real motors). The only manual step is physically placing the
# arm at its reference pose — that defines "zero" and cannot be automated.
#
# Bimanual default buses: right_arm=can0, left_arm=can1.  Install: provision-hardware.sh
set -eo pipefail
RIGHT_CAN="${RIGHT_CAN:-can0}"
LEFT_CAN="${LEFT_CAN:-can1}"

need() { command -v "$1" >/dev/null || { echo "missing '$1' — run scripts/provision-hardware.sh first"; exit 1; }; }
need openarm-can-configure-socketcan-4-arms
need openarm-can-zero-position-calibration
need openarm-can-cli

echo ">> 1/5  Configure SocketCAN (CAN-FD) on both buses"
sudo openarm-can-configure-socketcan-4-arms "$RIGHT_CAN" -fd
sudo openarm-can-configure-socketcan-4-arms "$LEFT_CAN"  -fd

echo ">> 2/5  Discover motors on each bus (every joint must be listed)"
openarm-can-cli -i "$RIGHT_CAN" discover || true
openarm-can-cli -i "$LEFT_CAN"  discover || true
read -rp "   Did BOTH buses list all motors? [y/N] " a; [ "$a" = y ] || { echo "Fix wiring / motor IDs first (openarm-can-cli change_id)."; exit 1; }

echo ">> 3/5  Motor health / sampling check"
openarm-can-motor-sampling-check --all 500 "$RIGHT_CAN" -fd || true
openarm-can-motor-sampling-check --all 500 "$LEFT_CAN"  -fd || true

echo ">> 4/5  ZERO CALIBRATION"
echo "   Physically move the arm to its REFERENCE pose now (the assembly zero pose"
echo "   where every joint should read 0). Hold it steady — this position becomes zero."
read -rp "   Arm held at the reference pose? [y/N] " a; [ "$a" = y ] || exit 1
openarm-can-zero-position-calibration --canport "$RIGHT_CAN" --arm-side right_arm
openarm-can-zero-position-calibration --canport "$LEFT_CAN"  --arm-side left_arm

echo ">> 5/5  Verify (OpenArm spec: every joint within ±0.05 rad of zero at reference)"
echo "   In another terminal:"
echo "     ros2 launch openarm_bringup openarm.bimanual.launch.py use_fake_hardware:=false"
echo "     ros2 topic echo /joint_states   # all positions ~0.00 at the reference pose"
echo
echo "DONE. Re-run only if a motor is reseated or replaced."
