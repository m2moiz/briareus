#!/usr/bin/env bash
# Play the beat-synced Macarena with the 103 BPM click track.
# The click plays on the Mac; the robot dances in the VM. They're started together
# by firing the audio at the robot's t=0 (when it sends the trajectory), so both
# 4-beat count-ins line up. Watch the arm: open vnc://localhost:5901 (pw: openarm)
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLICK="$ROOT/assets/macarena_click_103bpm.wav"
mkdir -p "$ROOT/assets"
[ -f "$CLICK" ] || { echo ">> generating click track…"; python3 "$ROOT/scripts/make-click-track.py" "$CLICK"; }
limactl shell openarm bash -c 'cat > ~/macarena_synced.py' < "$ROOT/scripts/macarena_synced.py"

echo ">> ensuring sim is up (move_group + 5 controllers)…"
limactl shell openarm bash -s <<'VMEOF'
source /opt/ros/humble/setup.bash; source ~/ros2_ws/install/setup.bash; export DISPLAY=:1
if ! pgrep -x move_group >/dev/null; then
  setsid nohup bash -c 'source /opt/ros/humble/setup.bash; source ~/ros2_ws/install/setup.bash; export DISPLAY=:1 LIBGL_ALWAYS_SOFTWARE=1; exec ros2 launch openarm_bimanual_moveit_config demo.launch.py' </dev/null >/tmp/mg.log 2>&1 &
  disown || true
  for i in $(seq 1 40); do sleep 2; grep -q "You can start planning now" /tmp/mg.log && break; done; sleep 3
fi
for c in joint_state_broadcaster left_joint_trajectory_controller right_joint_trajectory_controller left_gripper_controller right_gripper_controller; do
  ros2 run controller_manager spawner "$c" -c /controller_manager >/dev/null 2>&1 || true
done
echo "   controllers active: $(ros2 control list_controllers 2>/dev/null | grep -c active)/5"
VMEOF

echo ">> starting dance + click (count-in aligns them)…"
LOG="$(mktemp)"
limactl shell openarm bash -lc 'source /opt/ros/humble/setup.bash; source ~/ros2_ws/install/setup.bash; python3 ~/macarena_synced.py' >"$LOG" 2>&1 &
ROBOT=$!
# fire the audio the instant the robot reaches t=0 (trajectory sent)
for i in $(seq 1 600); do grep -q "trajectories sent" "$LOG" 2>/dev/null && break; sleep 0.05; done
afplay "$CLICK" >/dev/null 2>&1 &
CLICK_PID=$!
wait "$ROBOT"
kill "$CLICK_PID" 2>/dev/null || true
rm -f "$LOG"
echo ">> done — dance finished on the beat grid"
