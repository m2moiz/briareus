#!/usr/bin/env bash
# Install OpenArm REAL-HARDWARE (CAN) deployment packages on Ubuntu 22.04/24.04.
#
# Run this on the Linux machine that will be wired to the physical arm (or in the
# Lima VM to stage it). After this + a workspace rebuild, the OpenArm stack can be
# launched with `use_fake_hardware:=false` to drive the real Damiao motors.
#
# Sim needs none of this; it's purely the hardware path.  See HARDWARE.md.
set -eo pipefail

echo ">> 1/3  OpenArm CAN library (openarm_can) from the official PPA"
# libopenarm-can-dev = headers/lib that openarm_hardware links against.
# openarm-can-utils  = OpenArm CAN command-line tools.
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:openarm/main
sudo apt-get update
sudo apt-get install -y libopenarm-can-dev openarm-can-utils

echo ">> 2/3  SocketCAN userspace tools (slcand for the slcan bridge; candump/cansend to debug)"
sudo apt-get install -y can-utils

echo ">> 3/3  Build openarm_hardware (the ros2_control SystemInterface plugin)"
WS="${ROS2_WS:-$HOME/ros2_ws}"
if [ -d "$WS/src" ]; then
  source /opt/ros/humble/setup.bash
  ( cd "$WS" && colcon build --packages-select openarm_hardware && source install/setup.bash )
  echo "   built openarm_hardware in $WS"
else
  echo "   (no workspace at $WS — clone openarm_ros2 + openarm_description into \$WS/src,"
  echo "    then: cd \$WS && colcon build --packages-select openarm_hardware)"
fi

echo
echo "DONE. Hardware packages installed. Next:"
echo "  - bring up CAN:  sudo ip link set can0 type can bitrate 1000000 && sudo ip link set up can0"
echo "  - launch real:   ros2 launch openarm_bringup openarm.bimanual.launch.py use_fake_hardware:=false"
