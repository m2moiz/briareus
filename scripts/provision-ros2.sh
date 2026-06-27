#!/usr/bin/env bash
# Provisions ROS 2 Humble + builds openarm_ros2 (mock hardware) inside the
# Ubuntu 22.04 Lima guest. Run via: limactl shell openarm bash -s < this-file
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

echo "### [1/6] locale + base packages"
sudo apt-get update -y
sudo apt-get install -y locales curl gnupg software-properties-common git
sudo locale-gen en_US en_US.UTF-8 >/dev/null
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

echo "### [2/6] add ROS 2 apt repository"
sudo add-apt-repository -y universe
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
http://packages.ros.org/ros2/ubuntu jammy main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null

echo "### [3/6] install ROS 2 Humble desktop + tools (LONG step)"
sudo apt-get update -y
sudo apt-get install -y ros-humble-desktop ros-dev-tools \
  python3-colcon-common-extensions python3-vcstool python3-rosdep

echo "### [4/6] install openarm_ros2 ros2_control + MoveIt deps"
sudo apt-get install -y \
  ros-humble-controller-manager ros-humble-gripper-controllers ros-humble-hardware-interface \
  ros-humble-joint-state-broadcaster ros-humble-joint-trajectory-controller \
  ros-humble-forward-command-controller ros-humble-moveit-configs-utils ros-humble-moveit-planners \
  ros-humble-moveit-ros-move-group ros-humble-moveit-ros-visualization ros-humble-moveit-simple-controller-manager

echo "### [5/6] clone + build openarm_ros2 (mock hardware, no CAN)"
mkdir -p ~/ros2_ws/src
[ -d ~/ros2_ws/src/openarm_ros2/.git ] \
  || git clone https://github.com/enactic/openarm_ros2 ~/ros2_ws/src/openarm_ros2
source /opt/ros/humble/setup.bash
cd ~/ros2_ws && colcon build --symlink-install --packages-ignore openarm_hardware

echo "### [6/6] persist sourcing in ~/.bashrc"
grep -qxF 'source /opt/ros/humble/setup.bash'   ~/.bashrc || echo 'source /opt/ros/humble/setup.bash'   >> ~/.bashrc
grep -qxF 'source ~/ros2_ws/install/setup.bash' ~/.bashrc || echo 'source ~/ros2_ws/install/setup.bash' >> ~/.bashrc

echo "### PROVISION DONE — openarm packages built:"
source ~/ros2_ws/install/setup.bash
ros2 pkg list 2>/dev/null | grep -i openarm || echo "(no openarm pkgs found — check build log)"
