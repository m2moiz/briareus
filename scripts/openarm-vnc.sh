#!/usr/bin/env bash
# Launch RViz2 / MoveIt from the 'openarm' Lima VM via an IN-VM VNC display.
#
# Why VNC and not X11 forwarding: RViz's renderer (OGRE) needs a real OpenGL
# context. X11 forwarding to XQuartz can only offer *indirect* GLX, which cannot
# supply compatible framebuffer configs -> "No matching fbConfigs / Unable to
# create a suitable GLXContext". VNC runs a virtual X server (Xvnc) INSIDE the VM,
# so RViz renders locally on software Mesa (llvmpipe, a DIRECT context) and VNC
# only ships finished pixels to the Mac. No GLX-over-the-wire, so it just works.
#
# Connect from the Mac after this prints "VNC ready":
#   open vnc://localhost:5901      # macOS Screen Sharing; password: openarm
#
# Usage:
#   ./openarm-vnc.sh moveit   # MoveIt 2 bimanual demo (default) — the real thing
#   ./openarm-vnc.sh rviz     # bare RViz2
#   ./openarm-vnc.sh smoke    # headless: start Xvnc, run rviz ~8s, check GL — no human needed
set -eo pipefail

MODE="${1:-moveit}"
DISP=":1"          # Xvnc display :1  ->  VNC port 5901
VNCPORT=5901

# Everything below runs INSIDE the VM. No ssh -Y, no XQuartz — DISPLAY is the
# in-VM Xvnc, so a plain `limactl shell` is all we need. Args pass through bash -s.
run_vm() { limactl shell openarm bash -s "$@"; }

# Open the Mac VNC viewer (only for interactive modes, not smoke).
open_viewer() { sleep 3; open "vnc://localhost:${VNCPORT}" 2>/dev/null || true; }

if [ "$MODE" = "moveit" ] || [ "$MODE" = "rviz" ]; then open_viewer & fi

run_vm "$MODE" "$DISP" <<'VMEOF'
set -eo pipefail
MODE="${1:?}"; DISP="${2:?}"

# --- 1. one-time provision (idempotent: skipped once vnc tooling is present) ---
VNCSRV="$(command -v tigervncserver || command -v vncserver || true)"
if [ -z "$VNCSRV" ]; then
  echo ">> installing VNC tooling (one time)…"
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    tigervnc-standalone-server tigervnc-common openbox dbus-x11 mesa-utils >/dev/null
  VNCSRV="$(command -v tigervncserver || command -v vncserver)"
fi

# --- 2. VNC password (fixed: openarm) ---
mkdir -p ~/.vnc
if [ ! -f ~/.vnc/passwd ]; then
  echo openarm | vncpasswd -f > ~/.vnc/passwd
  chmod 600 ~/.vnc/passwd
fi

# --- 3. session startup: a tiny WM, with software GL forced ---
cat > ~/.vnc/xstartup <<'X'
#!/bin/sh
unset SESSION_MANAGER DBUS_SESSION_BUS_ADDRESS
export LIBGL_ALWAYS_SOFTWARE=1
exec openbox
X
chmod +x ~/.vnc/xstartup

# --- 4. (re)start the Xvnc display on :1, bound on all ifaces so Lima forwards it ---
"$VNCSRV" -kill "$DISP" >/dev/null 2>&1 || true
"$VNCSRV" "$DISP" -geometry 1920x1080 -depth 24 -localhost no \
  -SecurityTypes VncAuth -xstartup ~/.vnc/xstartup
trap '"'"$VNCSRV"'" -kill "'"$DISP"'" >/dev/null 2>&1 || true' EXIT

# --- 5. ROS env + force software Mesa (DIRECT context on the in-VM display) ---
export DISPLAY="$DISP"
source /opt/ros/humble/setup.bash
source ~/ros2_ws/install/setup.bash
export LIBGL_ALWAYS_SOFTWARE=1
export LP_NUM_THREADS="$(nproc)"

# Clean slate: a dead RViz (e.g. an old X11 attempt) leaves its launch +
# move_group + controllers alive; repeated runs then stack and fight over the
# ROS graph, and the new RViz never maps. Kill any prior launch before starting.
# (Patterns are specific node names — none match this 'bash -s' line, so no self-kill.)
pkill -f 'demo.launch.py'            2>/dev/null || true
pkill -x move_group                  2>/dev/null || true
pkill -x rviz2                       2>/dev/null || true
pkill -x ros2_control_node           2>/dev/null || true
pkill -f 'controller_manager/spawner' 2>/dev/null || true
sleep 2

case "$MODE" in
  smoke)
    echo ">> smoke: launching rviz2 for ~8s against $DISPLAY, capturing GL output…"
    ( rviz2 >/tmp/rviz_smoke.log 2>&1 & echo $! >/tmp/rviz_smoke.pid ) || true
    sleep 8
    kill "$(cat /tmp/rviz_smoke.pid)" 2>/dev/null || true
    sleep 1
    echo "----- rviz smoke log (tail) -----"
    tail -n 40 /tmp/rviz_smoke.log || true
    echo "----- verdict -----"
    if grep -q "Unable to create a suitable GLXContext\|Failed to create an OpenGL context" /tmp/rviz_smoke.log; then
      echo "FAIL: OGRE still cannot get a GL context."
      exit 1
    else
      echo "PASS: no GLXContext failure — RViz got an OpenGL context on the VNC display."
    fi
    ;;
  rviz)   rviz2 ;;
  moveit) ros2 launch openarm_bimanual_moveit_config demo.launch.py ;;
  *) echo "usage: openarm-vnc.sh {moveit|rviz|smoke}"; exit 2 ;;
esac
VMEOF
