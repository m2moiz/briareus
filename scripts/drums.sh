#!/usr/bin/env bash
# Bimanual drum beat (alternating toms) with a synced drum loop.
# Brings the arm up with drumsticks rendered (fake hardware) + a Foxglove bridge,
# plays a beat in sim, and plays the matching audio on the Mac. They start together
# so the 4-beat count-ins line up. Watch it: open Foxglove -> ws://localhost:8765.
#
# The VM-side block is fed via `bash -s` (stdin), so the pkills match the real ROS
# processes and never the launcher's own shell.
#   scripts/drums.sh [BPM] [BARS]      # defaults: 90 BPM, 4 bars
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VM=openarm
BPM="${1:-90}"
BARS="${2:-4}"
LOOP="$ROOT/assets/drum_loop_${BPM%.*}bpm.wav"

if ! limactl list 2>/dev/null | grep -qE "^${VM}[[:space:]]+Running"; then
  echo ">> starting VM '${VM}'..."; limactl start "$VM"
fi

mkdir -p "$ROOT/assets"
[ -f "$LOOP" ] || { echo ">> generating drum loop..."; python3 "$ROOT/scripts/make-drum-loop.py" "$LOOP" "$BPM" "$BARS"; }

limactl shell "$VM" bash -c 'cat > ~/drumbeat.py'     < "$ROOT/scripts/drumbeat.py"
limactl shell "$VM" bash -c 'cat > ~/drums.launch.py' < "$ROOT/scripts/drums.launch.py"

echo ">> bringing up the arm with drumsticks (fake hw) + Foxglove bridge..."
limactl shell "$VM" bash -s <<'VMEOF'
source /opt/ros/humble/setup.bash; source ~/ros2_ws/install/setup.bash
# clean any prior ROS so there is exactly one bringup, using the stick description
pkill -x ros2_control_node     2>/dev/null || true
pkill -f foxglove_bridge       2>/dev/null || true
pkill -f robot_state_publisher 2>/dev/null || true
pkill -f drums.launch          2>/dev/null || true
pkill -f spawner               2>/dev/null || true
sleep 1
setsid nohup bash -c 'source /opt/ros/humble/setup.bash; source ~/ros2_ws/install/setup.bash; exec ros2 launch ~/drums.launch.py' </dev/null >/tmp/drums_bringup.log 2>&1 &
disown || true
# wait for the control node, then spawn the controllers explicitly with retries
# (more robust than relying on the launch's timers when the VM is busy)
for i in $(seq 1 30); do sleep 1; ros2 control list_controllers >/dev/null 2>&1 && break; done
for c in joint_state_broadcaster left_joint_trajectory_controller right_joint_trajectory_controller left_gripper_controller right_gripper_controller; do
  ros2 run controller_manager spawner "$c" -c /controller_manager >/dev/null 2>&1 || true
done
sleep 2
echo "   controllers active: $(ros2 control list_controllers 2>/dev/null | grep -c active)/5"
VMEOF

open -a Foxglove 2>/dev/null || echo "(Foxglove app not found — install it; the bridge still runs)"
echo ">> connect Foxglove to ws://localhost:8765 (add a 3D panel) to watch the sticks"

echo ">> starting drum beat + audio (count-in aligns them)..."
LOG="$(mktemp)"
limactl shell "$VM" bash -lc "source /opt/ros/humble/setup.bash; source ~/ros2_ws/install/setup.bash; python3 ~/drumbeat.py $BPM $BARS" >"$LOG" 2>&1 &
ROBOT=$!
# fire the audio the instant the robot sends its trajectories (t=0), so count-ins align
for i in $(seq 1 600); do grep -q "trajectories sent" "$LOG" 2>/dev/null && break; sleep 0.05; done
afplay "$LOOP" >/dev/null 2>&1 &
APID=$!
wait "$ROBOT"
kill "$APID" 2>/dev/null || true
rm -f "$LOG"
echo ">> beat done. The arm + bridge stay up — run 'just drums' to replay, or 'just stop' to tear down."
