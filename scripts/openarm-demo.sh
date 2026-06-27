#!/usr/bin/env bash
# Launch the FULL OpenArm sim demo from the Mac:
#   VM up -> robot bringup (fake hw) -> wiggle motion -> Foxglove bridge -> open Foxglove.
# Connect Foxglove to ws://localhost:8765 (3D panel). Ctrl-C here stops everything.
#
# The VM-side block is fed via `bash -s` (stdin), NOT `bash -lc '...'`, so the
# cleanup pkills match the real ROS processes and never the launcher's own shell.
set -e
VM=openarm
PROJ="$(cd "$(dirname "$0")/.." && pwd)"

if ! limactl list 2>/dev/null | grep -qE "^${VM}[[:space:]]+Running"; then
  echo ">>> starting VM '${VM}'..."
  limactl start "$VM"
fi

# push the latest wiggle node into the VM
limactl shell "$VM" bash -c 'cat > ~/wiggle.py' < "$PROJ/scripts/wiggle.py"

open -a Foxglove 2>/dev/null || echo "(Foxglove app not found — install it; the bridge still runs)"

echo "=================================================================="
echo " OpenArm demo: robot + wiggle + Foxglove bridge"
echo " In Foxglove:  Open Connection -> ws://localhost:8765 -> add 3D panel"
echo " Ctrl-C here stops everything in the VM."
echo "=================================================================="

exec limactl shell "$VM" bash -s <<'VMEOF'
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash

cleanup() {
  echo; echo ">>> stopping ROS in the VM..."
  pkill -x ros2_control_node    2>/dev/null || true
  pkill -f foxglove_bridge      2>/dev/null || true
  pkill -f robot_state_publisher 2>/dev/null || true
  pkill -f wiggle.py            2>/dev/null || true
  pkill -f bimanual.launch      2>/dev/null || true
  pkill -f spawner              2>/dev/null || true
  sleep 1
}
trap cleanup EXIT INT TERM

echo ">>> starting bringup (fake hardware)..."
ros2 launch openarm_bringup openarm.bimanual.launch.py use_fake_hardware:=true >/tmp/bringup.log 2>&1 &
for _ in $(seq 1 30); do
  ros2 node list 2>/dev/null | grep -q controller_manager && break
  sleep 1
done
echo ">>> robot up; starting wiggle motion"
python3 ~/wiggle.py >/tmp/wiggle.log 2>&1 &
sleep 1
echo ">>> CONNECT Foxglove now -> ws://localhost:8765   (Ctrl-C to stop)"
ros2 run foxglove_bridge foxglove_bridge --ros-args -p port:=8765 -p address:=0.0.0.0
VMEOF
