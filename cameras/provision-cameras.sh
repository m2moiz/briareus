#!/usr/bin/env bash
# Install the camera-calibration toolchain for the OpenArm cameras (perception route).
#   - UVC driver + intrinsic calibration (apt)
#   - easy_handeye2 for hand-eye extrinsics (source — not on apt)
# Run on the Linux box wired to the cameras + arm. Override ws with ROS2_WS=...
set -eo pipefail
WS="${ROS2_WS:-$HOME/ros2_ws}"

echo ">> 1/3  ROS camera + calibration packages (apt)"
sudo apt-get install -y \
  ros-humble-v4l2-camera ros-humble-camera-calibration ros-humble-image-pipeline \
  ros-humble-camera-info-manager ros-humble-cv-bridge v4l-utils
sudo apt-get install -y python3-transforms3d 2>/dev/null || true   # easy_handeye2 dep

echo ">> 2/3  easy_handeye2 (hand-eye calibration) from source"
mkdir -p "$WS/src"
if [ ! -d "$WS/src/easy_handeye2" ]; then
  git clone --depth 1 https://github.com/marcoesposito1988/easy_handeye2.git "$WS/src/easy_handeye2"
fi
source /opt/ros/humble/setup.bash
( cd "$WS"
  rosdep install --from-paths src/easy_handeye2 --ignore-src -y 2>/dev/null || true
  colcon build --packages-up-to easy_handeye2 )

echo ">> 3/3  verify"
source "$WS/install/setup.bash"
ros2 pkg list 2>/dev/null | grep -E "easy_handeye2|v4l2_camera|camera_calibration" | sed 's/^/  /'
echo "DONE. Cameras: plug in -> cameras/discover-cameras.sh -> intrinsics -> hand-eye."
