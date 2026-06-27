#!/usr/bin/env bash
# Launch X-forwarded GUI apps from the 'openarm' Lima VM onto XQuartz.
# Prereqs: XQuartz installed + running on the Mac (this script starts it).
# RUN THIS IN YOUR OWN TERMINAL (it needs your GUI display) — not from an agent shell.
#
# Usage:
#   ./openarm-gui.sh test     # xeyes — proves X forwarding works at all
#   ./openarm-gui.sh gl       # glxgears + renderer string (shows llvmpipe = software GL)
#   ./openarm-gui.sh rviz     # bare RViz2
#   ./openarm-gui.sh moveit   # MoveIt 2 demo (bimanual) — the real thing
set -e

open -a XQuartz 2>/dev/null || { echo "XQuartz not installed — install it first"; exit 1; }
sleep 2

# Get XQuartz's REAL display from launchd. `just`/sh may not inherit DISPLAY, and
# :0 lacks XQuartz's auth cookie (keyed to the launchd-path display), so forwarding
# silently fails. launchctl returns e.g. /private/tmp/.../org.xquartz:0 after login.
_lc_disp="$(launchctl getenv DISPLAY 2>/dev/null)"
export DISPLAY="${_lc_disp:-${DISPLAY:-:0}}"
echo "using DISPLAY=$DISPLAY"

SSHCFG="$HOME/.lima/openarm/ssh.config"
[ -f "$SSHCFG" ] || { echo "Lima ssh config missing — is the VM up? (limactl list)"; exit 1; }
# macOS ssh defaults XAuthLocation to /usr/X11R6/bin/xauth (gone on modern macOS);
# XQuartz ships xauth at /opt/X11/bin/xauth — point ssh there or X11 forwarding silently fails.
XAUTH=/opt/X11/bin/xauth
# Lima's ssh.config sets ControlMaster/ControlPath; the persistent master socket was
# opened WITHOUT X11 forwarding, so a plain `ssh -Y` reuses it and -Y is ignored.
# Force a fresh, non-multiplexed connection so X11 forwarding actually takes effect.
SSH=(ssh -F "$SSHCFG" -Y -o "XAuthLocation=$XAUTH" -o ControlMaster=no -o ControlPath=none lima-openarm)

# LIBGL_ALWAYS_SOFTWARE=1 forces Mesa llvmpipe in the guest (the only GL path that
# works over forwarding here) and avoids slow/broken indirect-GLX negotiation.
SRC='source /opt/ros/humble/setup.bash; source ~/ros2_ws/install/setup.bash; export LIBGL_ALWAYS_SOFTWARE=1; export LP_NUM_THREADS=$(nproc)'

case "${1:-moveit}" in
  test)   "${SSH[@]}" 'xeyes' ;;
  gl)     "${SSH[@]}" 'export LIBGL_ALWAYS_SOFTWARE=1; glxinfo | grep -i "renderer string"; glxgears' ;;
  rviz)   "${SSH[@]}" "$SRC; rviz2" ;;
  moveit) "${SSH[@]}" "$SRC; ros2 launch openarm_bimanual_moveit_config demo.launch.py" ;;
  *) echo "usage: $0 {test|gl|rviz|moveit}"; exit 1 ;;
esac
