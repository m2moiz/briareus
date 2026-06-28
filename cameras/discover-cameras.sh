#!/usr/bin/env bash
# Discover the OpenArm UVC cameras and print each one's stable USB PORT PATH and
# supported formats — so you can fill cameras/99-openarm-cameras.rules and pin
# the three identical cameras to stable names. Run with the cameras plugged in.
set -eo pipefail
command -v v4l2-ctl >/dev/null || { echo "install v4l-utils (cameras/provision-cameras.sh)"; exit 1; }

echo "=== capture devices, USB port path (for udev KERNELS==) and formats ==="
for d in /dev/video*; do
  [ -e "$d" ] || continue
  v4l2-ctl -d "$d" --all 2>/dev/null | grep -qi "Video Capture" || continue   # skip metadata nodes
  card=$(v4l2-ctl -d "$d" --info 2>/dev/null | awk -F': ' '/Card type/{print $2}')
  port=$(udevadm info -a -n "$d" 2>/dev/null | awk -F'"' '/KERNELS=="[0-9]+-[0-9]/{print $2; exit}')
  echo "  $d   [$card]"
  echo "      USB port (KERNELS==):  $port"
  v4l2-ctl -d "$d" --list-formats-ext 2>/dev/null | awk '/\[[0-9]\]/{f=$0} /Size: Discrete/{print "        "f" "$3}' | sort -u | head -8
  echo
done
echo "Copy each USB port path into cameras/99-openarm-cameras.rules (KERNELS==),"
echo "then: sudo cp cameras/99-openarm-cameras.rules /etc/udev/rules.d/ &&"
echo "      sudo udevadm control --reload-rules && sudo udevadm trigger"
