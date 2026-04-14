# Bill of Materials (BOM)

| # | Component | Qty | Spec | Est. Cost (USD) |
|---|-----------|-----|------|-----------------|
| 1 | ESP32-WROOM-32 Dev Board | 1 | 240MHz, WiFi/BT, USB-C | $5 |
| 2 | Raspberry Pi 4 Model B | 1 | 4GB RAM, Bookworm OS | $55 |
| 3 | PCA9685 PWM Module | 1 | 16-channel, 12-bit, I2C | $3 |
| 4 | MG996R Servo (360°) | 4 | Continuous rotation, 10kg·cm | $16 |
| 5 | MG90S Servo (180°) | 3 | Standard, 1.8kg·cm | $6 |
| 6 | Power Supply | 1 | 6V 4A DC (10A recommended) | $8 |
| 7 | USB Cable (Type-A to Micro/C) | 1 | Pi to ESP32 data connection | $2 |
| 8 | Jumper Wires | 20 | Male-to-female, 20cm | $2 |
| 9 | Breadboard (optional) | 1 | For prototyping connections | $3 |
| 10 | 3D Printed Arm Parts | 1 set | PLA/PETG, Bambu Lab printer | ~$5 |
| 11 | 6203 Bearings | 2 | For base rotation joint | $4 |
| 12 | M3 Screws + Nuts | 20 | For assembly | $2 |
| 13 | MicroSD Card | 1 | 32GB for Raspberry Pi OS | $5 |
| **Total** | | | | **~$116** |

## Notes

- MG996R 360° variant has internal potentiometer removed — no position feedback
- PSU must share GND with ESP32 and PCA9685
- 3D printed parts designed in Bambu Studio, printed on Bambu Lab H2D
