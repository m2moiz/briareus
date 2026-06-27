#!/usr/bin/env bash
# Validate the REAL-hardware launch path entirely in SOFTWARE, using virtual CAN
# (vcan) — no arm, no USB-CAN adapter, no risk.
#
# Run ONLY on a machine WITHOUT a real OpenArm / USB-CAN adapter: it creates
# virtual buses named can0 + can1 to match the bimanual defaults (right=can0,
# left=can1), and refuses to touch a real CAN device.
#
# PROVES: the openarm_hardware plugin (OpenArmHW) loads, the launch + xacro +
#   ros2_control config parse with use_fake_hardware:=false, and the driver opens
#   the CAN socket (no CANSocketException) and emits motor frames.
# CANNOT prove (no motors reply on vcan): motor handshake, activation, motion.
#   Activation not completing is EXPECTED — that's the honest boundary.
#
# Run on Ubuntu (incl. the Lima VM) after scripts/provision-hardware.sh.
set -eo pipefail
WS="${ROS2_WS:-$HOME/ros2_ws}"

echo ">> 1/4  virtual buses can0 + can1 (bimanual = 2 buses; names match defaults)"
for c in can0 can1; do
  if ip link show "$c" >/dev/null 2>&1 && ! ip -d link show "$c" 2>/dev/null | grep -qw vcan; then
    echo "   REFUSING: '$c' exists and is not a vcan (a real CAN device?)."
    echo "   Run this only on a box WITHOUT the arm/adapter."; exit 1
  fi
done
if ! lsmod | grep -q '^vcan '; then
  sudo modprobe vcan 2>/dev/null \
    || { sudo apt-get install -y "linux-modules-extra-$(uname -r)"; sudo modprobe vcan; }
fi
for c in can0 can1; do
  ip link show "$c" >/dev/null 2>&1 || sudo ip link add dev "$c" type vcan
  sudo ip link set up "$c"
done
ip -brief link show type vcan | sed 's/^/   /'

source /opt/ros/humble/setup.bash; source "$WS/install/setup.bash"

echo ">> 2/4  capture frames the driver sends (candump can0 for ~14s, background)"
timeout 14 candump can0 > /tmp/vcan_dump.txt 2>&1 &

echo ">> 3/4  launch the REAL-hardware stack (use_fake_hardware:=false, default can0/can1)"
setsid ros2 launch openarm_bringup openarm.bimanual.launch.py use_fake_hardware:=false \
  > /tmp/vcan_launch.log 2>&1 &
LP=$!
sleep 12

echo ">> 4/4  results"
echo "-- plugin load + socket open --"
grep -iE "OpenArmHW|Loading hardware|Initialize|Configuration:|Successful .configure|Failed to initialize socket|CANSocketException|error|exception" \
  /tmp/vcan_launch.log | tail -16 | sed 's/^/   /' || true
echo "-- frames the driver emitted on can0: $(grep -c can0 /tmp/vcan_dump.txt 2>/dev/null || echo 0) --"

kill "$LP" 2>/dev/null || true
echo
echo "PASS if: OpenArmHW loaded AND no 'Failed to initialize socket' (socket opened on vcan)."
echo "Motor activation not completing with no motors is expected."
