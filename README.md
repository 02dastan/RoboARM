# BAURSAK ARM — AI-Driven Robotic Manipulator

A multi-tier robotic arm system designed for autonomous food handling (Baursak delivery) during the Nauryz celebration. Built by students at SDU University, Almaty, Kazakhstan.

## Architecture

```
┌──────────────┐     USB/Serial     ┌──────────────┐     I2C      ┌──────────────┐
│  Client      │◄──── WiFi ────────►│ Raspberry Pi │◄────────────►│   ESP32      │
│  (Phone/PC)  │     HTTP/WS        │  (Brain)     │   115200bd   │  (Bridge)    │
└──────────────┘                    └──────────────┘              └──────┬───────┘
                                                                        │ I2C
                                                                  ┌─────┴──────┐
                                                                  │  PCA9685   │
                                                                  │  16-ch PWM │
                                                                  └─────┬──────┘
                                                          ┌───┬───┬───┬─┴─┬───┬───┐
                                                         CH1 CH2 CH3 CH4 CH5 CH6 CH7
                                                         MG90S(×3)    MG996R(×4)
```

## Hardware

| Component | Spec | Role |
|-----------|------|------|
| ESP32-WROOM-32 | 240MHz, WiFi/BT | Serial bridge to PCA9685 |
| Raspberry Pi 4 | 4GB RAM, Bookworm | Web server, motion planning |
| PCA9685 | 16-ch, 12-bit PWM | Servo signal generation |
| MG90S × 3 | 180° standard | Wrist, gripper fine control |
| MG996R × 4 | 360° continuous | Base rotation, arm joints |
| PSU | 6V 4A (min 10A for all) | Servo power |

## Servo Channel Map

| Channel | Servo | Type | Range | Role |
|---------|-------|------|-------|------|
| CH1 | MG90S | 180° | 80°–180° | Gripper open/close |
| CH2 | MG90S | 180° | 0°–180° | Wrist tilt |
| CH3 | MG90S | 180° | 0°–180° | Wrist rotate |
| CH4 | MG996R | 360°* | 0°–180° | Elbow |
| CH5 | MG996R | 360°* | mirror CH6 | Shoulder (paired) |
| CH6 | MG996R | 360°* | 0°–180° | Shoulder (paired) |
| CH7 | MG996R | 360°* | -30°–220° | Base rotation |

*360° servos operated in 0–180° positional range via PWM mapping.

CH5 is automatically mirrored: `CH5 = 180 - CH6`

## Wiring

```
ESP32 GPIO21 (SDA) ──── PCA9685 SDA
ESP32 GPIO22 (SCL) ──── PCA9685 SCL
ESP32 3.3V ───────────── PCA9685 VCC
ESP32 GND ────────────── PCA9685 GND ──── PSU GND (COMMON!)
PSU 6V+ ──────────────── Servo VCC (red wires, all 7)
PSU GND ──────────────── Servo GND (brown wires, all 7)
PCA9685 CH1-CH7 ──────── Servo signal (orange wires)
Raspberry Pi USB ─────── ESP32 USB (Serial 115200)
```

⚠️ **CRITICAL**: PSU GND, ESP32 GND, and PCA9685 GND must be connected together.

## Quick Start

### 1. Flash ESP32
```bash
# Arduino IDE: Install "Adafruit PWM Servo Driver Library" + "Wire"
# Board: ESP32 Dev Module, 115200 baud
# Upload firmware/esp32/bridge.ino
```

### 2. Setup Raspberry Pi
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python server.py
```

### 3. Open Browser
```
http://<raspberry-pi-ip>:8080
Password: baursak2024
```

## Features

- **10 Built-in Modes** — Pre-calibrated baursak pickup sequences
- **Manual Control** — Real-time slider control per channel
- **Custom Mode Creator** — Build sequences with per-pose speed/mode
- **Record & Play** — Move arm manually, save poses, replay
- **Loop Mode** — Repeat any mode N times with pause
- **Mode Editor** — Edit saved modes, insert/delete poses
- **Auth** — Cookie-based session with password
- **Logging** — All mode saves/edits/deletes logged to `modes_log.txt`

## Serial Protocol (Pi ↔ ESP32)

| Command | Format | Description |
|---------|--------|-------------|
| Write All | `W c1 c2 c3 c4 c5 c6 c7\n` | Set all 7 channels |
| Write One | `I ch angle\n` | Set single channel |
| Heartbeat | `H\n` | Connection check |
| Response | `K\n` | Acknowledgment |

## Project Structure

```
baursak-arm/
├── firmware/
│   ├── esp32/
│   │   └── bridge.ino          # ESP32 Serial-to-PWM bridge
│   └── arduino/
│       └── sensor_node.ino     # Auxiliary sensor node (future)
├── backend/
│   ├── server.py               # Main FastAPI server
│   ├── motion.py               # MotionController class
│   ├── config.py               # All configuration
│   ├── poses.py                # Pose definitions
│   ├── sequences.py            # Built-in mode sequences
│   ├── storage.py              # Mode save/load/log
│   ├── pages.py                # HTML templates
│   ├── requirements.txt
│   └── scripts/
│       ├── setup.sh            # First-time Pi setup
│       └── monitor.sh          # System monitoring
├── docs/
│   ├── WIRING.md
│   ├── BOM.md
│   ├── CALIBRATION.md
│   └── baursak_arm.tex         # LaTeX documentation
├── .gitignore
└── README.md
```

## Authors

- **Dastan Tolkynov** — SDU University, Computer Science
- Built for Nauryz 2025 celebration

## License

MIT
