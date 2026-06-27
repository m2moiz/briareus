# Real-hardware deployment (Linux + CAN)

The sim needs none of this. This is the path to drive the **physical OpenArm** from a
Linux machine wired to the arm's CAN bus. Tested on Ubuntu 22.04 (arm64 + amd64).

## 1. Install the hardware packages

One command (idempotent):

```bash
bash scripts/provision-hardware.sh
```

It installs:

| Package | From | Purpose |
|---|---|---|
| `libopenarm-can-dev`, `openarm-can-utils`, `python3-openarm-can` | OpenArm PPA `ppa:openarm/main` | The `openarm_can` library + Python bindings the hardware interface links against |
| `can-utils` | apt | SocketCAN tools — `slcand` (slcan bridge), `candump`/`cansend` (debug), `can0` bring-up |
| `openarm_hardware` | built from `openarm_ros2` | ros2_control `SystemInterface` plugin `openarm_hardware/OpenArmHW` |

(ros2_control, ros2_controllers, MoveIt come from the base ROS install used for sim.)

## 2. Bring up the CAN interface

**Native USB-CAN adapter (on a Linux host wired to the arm):**
```bash
sudo ip link set can0 type can bitrate 1000000
sudo ip link set up can0
candump can0            # sanity: see motor frames
```

**slcan bridge (e.g. a CANable, incl. the Mac→Lima-VM serial bridge):**
```bash
sudo slcand -o -c -s8 /dev/ttyACM0 can0   # -s8 = 1 Mbit/s
sudo ip link set up can0
```

## 3. Launch against the real arm

```bash
ros2 launch openarm_bringup openarm.bimanual.launch.py use_fake_hardware:=false
```

This loads `openarm_hardware/OpenArmHW` instead of the sim's `mock_components`, opens
`can0`, and drives the real Damiao motors. The same controllers, topics, MoveIt config,
and the motion scripts (`wiggle.py` / `bimanual_sequence.py` / `macarena.py`) all apply
unchanged.

## 4. Before the first real run — safety

1. **Zero the motors** (OpenArm calibration): every joint must read within ±0.05 rad of
   zero at the reference pose. Mis-zeroing makes every scripted pose wrong.
2. **Run calibration**: `python3 calibrate.py` → writes `motion_limits.yaml`; the scripts
   then pace themselves to safe per-joint velocities (`speed_scale` starts low).
3. **Collision-check** any near-limit poses (macarena) in MoveIt first.
4. **Keep an e-stop in hand**, run slow + supervised.
