#!/usr/bin/env bash
# Start the OpenArm stack (fake hardware) + Foxglove bridge inside the Lima VM.
# Then on your Mac:  Foxglove -> Open Connection -> ws://localhost:8765
# Ctrl-C here cleanly stops everything in the VM.
#
# Run this from your Mac terminal:  ~/openarm-ws/openarm-foxglove.sh
set -e

# make sure the VM is up
if ! limactl list 2>/dev/null | grep -qE '^openarm\s+Running'; then
  echo ">>> openarm VM not running — starting it..."
  limactl start openarm
fi

echo "=================================================================="
echo " Starting OpenArm (bimanual, fake hardware) + Foxglove bridge"
echo " When you see 'CONNECT NOW', open Foxglove on your Mac:"
echo "     Open Connection  ->  Foxglove WebSocket  ->  ws://localhost:8765"
echo " Press Ctrl-C here to stop everything."
echo "=================================================================="
echo

exec limactl shell openarm bash -lc '
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

cleanup() {
  echo; echo ">>> shutting down ROS in the VM..."
  pkill -f "openarm.bimanual"      2>/dev/null || true
  pkill -f foxglove_bridge         2>/dev/null || true
  pkill -f robot_state_publisher   2>/dev/null || true
  pkill -f controller_manager      2>/dev/null || true
  pkill -f spawner                 2>/dev/null || true
  sleep 1
}
trap cleanup EXIT INT TERM

# Robot bringup (fake hardware). Logged to a file so the headless-RViz errors
# (no display in the VM) do not spam this terminal.
ros2 launch openarm_bringup openarm.bimanual.launch.py use_fake_hardware:=true \
  > /tmp/openarm_bringup.log 2>&1 &

sleep 6
echo ">>> robot up: controllers + /joint_states + /tf publishing."
echo ">>> CONNECT NOW:  Foxglove -> Open Connection -> ws://localhost:8765"
echo ">>> (Add a 3D panel; it loads the arm from /robot_description. Ctrl-C to stop.)"
echo

# Foxglove bridge in the foreground (Ctrl-C lands here -> trap cleans up).
ros2 run foxglove_bridge foxglove_bridge --ros-args -p port:=8765 -p address:=0.0.0.0
'
