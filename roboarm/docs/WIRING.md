# Wiring Diagram

## System Overview

```
┌─────────────┐    USB     ┌─────────────┐    I2C     ┌──────────┐
│ Raspberry   │◄──────────►│   ESP32     │◄──────────►│ PCA9685  │
│ Pi 4 (4GB)  │  115200bd  │ WROOM-32   │ GPIO21/22  │ PWM 16ch │
└─────────────┘            └─────────────┘            └────┬─────┘
                                                           │
                                   ┌───────────────────────┤
                                   │  Signal wires (orange) │
                            ┌──────┼──────┬──────┬──────┬──┴───┬──────┬──────┐
                            CH1    CH2    CH3    CH4    CH5    CH6    CH7
                            MG90S  MG90S  MG90S  996R   996R   996R   996R
                            grip   wrist  rot    elbow  shldr  shldr  base

                    ┌──────────────────────────────────────────────────────────┐
                    │              EXTERNAL PSU 6V 4A+                        │
                    │  V+ ──────── All servo VCC (red wires)                  │
                    │  GND ─┬───── All servo GND (brown wires)               │
                    │       ├───── ESP32 GND                                  │
                    │       └───── PCA9685 GND                                │
                    └──────────────────────────────────────────────────────────┘
```

## Pin Connections

### ESP32 → PCA9685
| ESP32 Pin | PCA9685 Pin | Wire Color |
|-----------|-------------|------------|
| GPIO 21   | SDA         | Blue       |
| GPIO 22   | SCL         | Yellow     |
| 3.3V      | VCC         | Red        |
| GND       | GND         | Black      |

### PCA9685 → Servos (signal only)
| PCA9685 Ch | Servo   | Type   |
|------------|---------|--------|
| 1          | MG90S   | Gripper |
| 2          | MG90S   | Wrist tilt |
| 3          | MG90S   | Wrist rotate |
| 4          | MG996R  | Elbow |
| 5          | MG996R  | Shoulder A (mirror) |
| 6          | MG996R  | Shoulder B (input) |
| 7          | MG996R  | Base rotation |

### Power
| Source | Destination | Notes |
|--------|-------------|-------|
| PSU 6V+ | All servo VCC | Red wires, parallel |
| PSU GND | All servo GND + ESP32 GND + PCA9685 GND | **COMMON GROUND CRITICAL** |

## ⚠️ Critical Notes

1. **Common GND**: PSU, ESP32, and PCA9685 GND must all be connected. Without common ground, servo signals won't work.

2. **Power budget**: 4× MG996R (2A each) + 3× MG90S (0.5A each) = 9.5A peak. Use 6V 10A PSU for simultaneous movement, or 6V 4A if not all moving at once.

3. **USB power**: Never power servos from ESP32 USB — it provides max 500mA, servos need 1-2A each.

4. **PCA9685 V+**: Leave disconnected if powering servos directly from PSU. Only use V+ if routing servo power through PCA9685 board.
