#!/usr/bin/env bash
# Build-only step (apt installs already done). NOTE: no `set -u` — ROS 2's
# setup.bash references unbound vars and trips strict mode.
set -eo pipefail

echo "### verify ROS 2 install is intact"
dpkg -s ros-humble-desktop >/dev/null 2>&1 && echo "  ros-humble-desktop: installed" || { echo "  MISSING ros-humble-desktop"; exit 1; }
for p in ros-humble-moveit-ros-move-group ros-humble-joint-trajectory-controller ros-humble-controller-manager; do
  dpkg -s "$p" >/dev/null 2>&1 && echo "  $p: ok" || echo "  WARN: $p missing"
done

# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash
echo "  ROS_DISTRO=$ROS_DISTRO"
ros2 --version 2>/dev/null || true

echo "### clone (idempotent) + build openarm_ros2 (mock hardware, no CAN)"
mkdir -p ~/ros2_ws/src
if [ ! -d ~/ros2_ws/src/openarm_ros2/.git ]; then
  rm -rf ~/ros2_ws/src/openarm_ros2
  git clone https://github.com/enactic/openarm_ros2 ~/ros2_ws/src/openarm_ros2
fi
cd ~/ros2_ws
colcon build --symlink-install --packages-ignore openarm_hardware

echo "### persist sourcing in ~/.bashrc"
grep -qxF 'source /opt/ros/humble/setup.bash'   ~/.bashrc || echo 'source /opt/ros/humble/setup.bash'   >> ~/.bashrc
grep -qxF 'source ~/ros2_ws/install/setup.bash' ~/.bashrc || echo 'source ~/ros2_ws/install/setup.bash' >> ~/.bashrc

echo "### BUILD DONE — openarm packages:"
source ~/ros2_ws/install/setup.bash
ros2 pkg list | grep -i openarm || echo "(no openarm pkgs — check build output above)"
