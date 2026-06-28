# OpenArm hackathon — task runner.  `just` to list, `just demo` to launch everything.
vm := "openarm"
root := justfile_directory()

# list available commands
default:
    @just --list

# 🚀 launch EVERYTHING: VM + robot + wiggle motion + Foxglove bridge, open Foxglove (Ctrl-C to stop)
demo:
    "{{root}}/scripts/openarm-demo.sh"

# robot + Foxglove bridge only (no auto-wiggle)
foxglove:
    "{{root}}/scripts/openarm-foxglove.sh"

# wiggle the arm (robot must already be running, e.g. via `just foxglove`)
wiggle:
    limactl shell {{vm}} bash -lc 'source /opt/ros/humble/setup.bash; source ~/ros2_ws/install/setup.bash; python3 ~/wiggle.py'

# interactive MoveIt in RViz via in-VM VNC — connect: open vnc://localhost:5901 (password: openarm)
moveit:
    "{{root}}/scripts/openarm-vnc.sh" moveit

# bare RViz2 via in-VM VNC (password: openarm)
rviz:
    "{{root}}/scripts/openarm-vnc.sh" rviz

# collision-aware MoveIt Macarena — every beat planned + collision-checked (watch: open vnc://localhost:5901)
moveit-dance:
    "{{root}}/scripts/moveit-dance.sh"

# beat-synced Macarena to a 103 BPM click track (audio on the Mac, arm in sim)
macarena-music:
    "{{root}}/scripts/macarena-music.sh"

# stop all ROS processes in the VM (VM stays up)
stop:
    "{{root}}/scripts/stop.sh"

# open a shell inside the VM
shell:
    limactl shell {{vm}}

# start / stop the VM itself
vm-up:
    limactl start {{vm}}
vm-down:
    limactl stop {{vm}}

# show VM + ROS status
status:
    -limactl list | grep -E 'NAME|{{vm}}'
    -limactl shell {{vm}} bash -lc 'pgrep -x ros2_control_node >/dev/null && echo "ROS: running" || echo "ROS: stopped"'
