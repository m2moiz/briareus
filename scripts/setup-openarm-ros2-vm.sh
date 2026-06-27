#!/usr/bin/env bash
#
# setup-openarm-ros2-vm.sh
# End-to-end ROS 2 (Humble) setup for OpenArm DEVELOPMENT inside an
# Ubuntu 22.04 (Jammy) VM — mock/fake hardware only (no CAN, no real arm).
#
# Target:  Ubuntu 22.04 LTS arm64 (e.g. UTM / VMware Fusion on Apple Silicon)
#          or x86-64 Ubuntu 22.04. ROS 2 Humble ships native arm64 debs, so
#          no emulation is needed on M-series Macs.
#
# What it does (idempotent — safe to re-run):
#   1. sanity-check the OS
#   2. set locale + add the ROS 2 apt repo
#   3. install ROS 2 Humble desktop + openarm_ros2's ros2_control & MoveIt deps
#   4. create ~/ros2_ws, clone enactic/openarm_ros2
#   5. colcon build  (MOCK ONLY: --packages-ignore openarm_hardware)
#   6. add the source lines to ~/.bashrc
#
# It does NOT install the CAN library or build the hardware interface — those
# belong on the native Linux host that drives the real arm (see "PART C" notes
# printed at the end).
#
set -euo pipefail

WS="${OPENARM_WS:-$HOME/ros2_ws}"
ROS_DISTRO="humble"

log()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

# --- 1. OS sanity check -----------------------------------------------------
log "Checking OS"
[ "$(uname -s)" = "Linux" ] || die "This script must run inside the Ubuntu VM, not on macOS."
command -v apt-get >/dev/null 2>&1 || die "apt not found — this needs Ubuntu/Debian."
. /etc/os-release
if [ "${UBUNTU_CODENAME:-}" != "jammy" ]; then
  warn "Detected '${UBUNTU_CODENAME:-unknown}', but ROS 2 $ROS_DISTRO targets Ubuntu 22.04 (jammy)."
  warn "Continuing anyway — apt may fail to find ros-$ROS_DISTRO-* packages if this is wrong."
fi
echo "Arch: $(dpkg --print-architecture)   Ubuntu: ${VERSION:-?}"

# --- 2. locale + ROS 2 apt repo --------------------------------------------
log "Configuring locale"
sudo apt-get update
sudo apt-get install -y locales curl gnupg software-properties-common
sudo locale-gen en_US en_US.UTF-8 >/dev/null
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8

log "Adding the ROS 2 apt repository (idempotent)"
sudo add-apt-repository -y universe
KEYRING=/usr/share/keyrings/ros-archive-keyring.gpg
if [ ! -f "$KEYRING" ]; then
  sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o "$KEYRING"
fi
echo "deb [arch=$(dpkg --print-architecture) signed-by=$KEYRING] \
http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo "$UBUNTU_CODENAME") main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list >/dev/null

# --- 3. install ROS 2 + OpenArm deps ---------------------------------------
log "Installing ROS 2 $ROS_DISTRO desktop + build tools (this is the long step)"
sudo apt-get update
sudo apt-get install -y \
  "ros-$ROS_DISTRO-desktop" ros-dev-tools \
  python3-colcon-common-extensions python3-vcstool python3-rosdep

log "Installing openarm_ros2 ros2_control + MoveIt dependencies"
sudo apt-get install -y \
  "ros-$ROS_DISTRO-controller-manager" \
  "ros-$ROS_DISTRO-gripper-controllers" \
  "ros-$ROS_DISTRO-hardware-interface" \
  "ros-$ROS_DISTRO-joint-state-broadcaster" \
  "ros-$ROS_DISTRO-joint-trajectory-controller" \
  "ros-$ROS_DISTRO-forward-command-controller" \
  "ros-$ROS_DISTRO-moveit-configs-utils" \
  "ros-$ROS_DISTRO-moveit-planners" \
  "ros-$ROS_DISTRO-moveit-ros-move-group" \
  "ros-$ROS_DISTRO-moveit-ros-visualization" \
  "ros-$ROS_DISTRO-moveit-simple-controller-manager"

# --- 4. workspace + clone ---------------------------------------------------
log "Setting up workspace at $WS"
mkdir -p "$WS/src"
if [ ! -d "$WS/src/openarm_ros2/.git" ]; then
  git clone https://github.com/enactic/openarm_ros2 "$WS/src/openarm_ros2"
else
  echo "openarm_ros2 already cloned — pulling latest"
  git -C "$WS/src/openarm_ros2" pull --ff-only || warn "git pull skipped (local changes?)"
fi

# --- 5. build (mock only) ---------------------------------------------------
log "Building workspace (mock hardware only — ignoring openarm_hardware)"
# shellcheck disable=SC1090
source "/opt/ros/$ROS_DISTRO/setup.bash"
cd "$WS"
colcon build --symlink-install --packages-ignore openarm_hardware

# --- 6. persist sourcing ----------------------------------------------------
log "Wiring up ~/.bashrc (idempotent)"
grep -qxF "source /opt/ros/$ROS_DISTRO/setup.bash" "$HOME/.bashrc" \
  || echo "source /opt/ros/$ROS_DISTRO/setup.bash" >> "$HOME/.bashrc"
grep -qxF "source $WS/install/setup.bash" "$HOME/.bashrc" \
  || echo "source $WS/install/setup.bash" >> "$HOME/.bashrc"

# --- done -------------------------------------------------------------------
cat <<EOF

✓ Done. Open a NEW terminal (or: source ~/.bashrc), then verify:

  ros2 -h
  ros2 launch openarm_bringup openarm.launch.py arm_type:=v10 use_fake_hardware:=true

  # bimanual:
  ros2 launch openarm_bringup openarm.bimanual.launch.py arm_type:=v10 use_fake_hardware:=true
  # MoveIt 2 demo:
  ros2 launch openarm_bimanual_moveit_config demo.launch.py
  # see the REAL launch args your clone exposes (resolves use_fake_hardware vs hardware_type):
  ros2 launch openarm_bringup openarm.launch.py --show-args

  # quick joint move test (after a bringup is running, in another terminal):
  ros2 action list

------------------------------------------------------------------------------
PART C — REAL ARM (do this on the native Linux host, NOT this VM/Mac):
  sudo add-apt-repository ppa:openarm/main
  sudo apt install -y libopenarm-can-dev openarm-can-utils
  cd \$WS && vcs import src < src/openarm_ros2/openarm.repos   # pulls openarm_can
  colcon build                                                # full, WITH openarm_hardware
  openarm-can-configure-socketcan can0                        # bring CAN up (re-run after replug)
  ros2 launch openarm_bringup openarm.launch.py arm_type:=v10 use_fake_hardware:=false can_interface:=can0
NOTE: OpenArm's real hardware is Linux-only (no macOS CAN driver). The VM is
for mock/sim dev; the physical arm needs a native Linux machine.
------------------------------------------------------------------------------
EOF
