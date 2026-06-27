#!/usr/bin/env bash
# Hide MoveIt's "ghost" overlays in RViz so you watch a CLEAN dance:
#   - Planned Path replay (translucent trajectory robot)  -> off
#   - Query Goal State (draggable colored ghost)          -> off
#   - Loop Animation                                       -> off
# The Scene Robot (the real, solid arm) is kept ON. Edits the moveit.rviz config
# in place (install + source copies). Idempotent. Relaunch RViz after (just moveit-dance).
#
# Run inside the VM / on the Linux box. Override the workspace with ROS2_WS=...
set -eo pipefail
WS="${ROS2_WS:-$HOME/ros2_ws}"
PKG=openarm_bimanual_moveit_config

for f in \
  "$WS/install/$PKG/share/$PKG/config/openarm_v2.0/moveit.rviz" \
  "$WS/src/openarm_ros2/$PKG/config/openarm_v2.0/moveit.rviz"; do
  [ -f "$f" ] || continue
  sed -i "s/Loop Animation: true/Loop Animation: false/" "$f"
  sed -i "s/Query Goal State: true/Query Goal State: false/" "$f"
  # IDEMPOTENT + precise: first make every Show Robot Visual visible (restores the
  # Scene Robot), THEN turn off ONLY the Planned Path one (the replica lives inside
  # the Loop Animation..Trajectory Topic block; the Scene Robot is outside it).
  sed -i "s/Show Robot Visual: false/Show Robot Visual: true/g" "$f"
  sed -i "/Loop Animation:/,/Trajectory Topic:/ s/Show Robot Visual: true/Show Robot Visual: false/" "$f"
  echo "patched $f"
done
echo "Done. Relaunch RViz (just moveit-dance) to see the clean view."
