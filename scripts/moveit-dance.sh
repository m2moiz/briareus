#!/usr/bin/env bash
# Run the collision-aware MoveIt Macarena reliably (sim).
# Every beat is planned + collision-checked by MoveIt, then executed.
# Watch it: connect a VNC viewer -> open vnc://localhost:5901  (password: openarm)
#
# Fixes a real bringup flake: under startup CPU load the arm trajectory
# controllers sometimes lose the spawn race and fail to configure. MoveIt can
# only execute through ACTIVE controllers, so this script (re)spawns any that
# didn't come up before running the dance.
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# ship the MoveIt motion scripts into the VM
limactl shell openarm bash -c 'cat > ~/moveit_motion.py'   < "$ROOT/scripts/moveit_motion.py"
limactl shell openarm bash -c 'cat > ~/macarena_moveit.py' < "$ROOT/scripts/macarena_moveit.py"

exec limactl shell openarm bash -s <<'VMEOF'
set -eo pipefail
source /opt/ros/humble/setup.bash; source ~/ros2_ws/install/setup.bash
export DISPLAY=:1
EXPECT="joint_state_broadcaster left_joint_trajectory_controller right_joint_trajectory_controller left_gripper_controller right_gripper_controller"

# 1. bring up move_group + controllers + RViz (on the VNC display) if not running
if ! pgrep -x move_group >/dev/null; then
  echo ">> bringing up MoveIt demo…"
  setsid nohup bash -c 'source /opt/ros/humble/setup.bash; source ~/ros2_ws/install/setup.bash; export DISPLAY=:1 LIBGL_ALWAYS_SOFTWARE=1; exec ros2 launch openarm_bimanual_moveit_config demo.launch.py' </dev/null >/tmp/mg.log 2>&1 &
  disown || true
  for i in $(seq 1 40); do sleep 2; grep -q "You can start planning now" /tmp/mg.log && break; done
  sleep 4
fi

# 2. reliability fix: respawn any controller that lost the startup race.
#    (strip ANSI colour codes first, else the name-anchored match never hits)
strip() { ros2 control list_controllers 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g'; }
for c in $EXPECT; do
  if ! strip | grep -qE "^[[:space:]]*$c[[:space:]].*active"; then
    echo ">> respawning $c (lost the startup spawn race)…"
    ros2 run controller_manager spawner "$c" -c /controller_manager >/dev/null 2>&1 || true
  fi
done
n=$(strip | grep -cE "[[:space:]]active([[:space:]]|$)")
echo ">> controllers active: $n/5"
[ "$n" -ge 5 ] || { echo "ERROR: not all 5 controllers active — try again"; exit 1; }

# 3. run the collision-aware dance
echo ">> running collision-aware Macarena via MoveIt (every beat collision-checked)…"
python3 ~/macarena_moveit.py
VMEOF
