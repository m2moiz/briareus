#!/usr/bin/env bash
# Stop all OpenArm ROS processes in the VM (the VM itself keeps running).
# Uses `bash -s` (stdin) so the pkills match real ROS procs, not this shell.
VM=openarm
limactl shell "$VM" bash -s <<'VMEOF'
pkill -x ros2_control_node     2>/dev/null || true
pkill -f foxglove_bridge       2>/dev/null || true
pkill -f robot_state_publisher 2>/dev/null || true
pkill -f wiggle.py             2>/dev/null || true
pkill -f bimanual.launch       2>/dev/null || true
pkill -f spawner               2>/dev/null || true
sleep 1
pgrep -x ros2_control_node >/dev/null && echo "ROS still running" || echo "ROS stopped"
VMEOF
