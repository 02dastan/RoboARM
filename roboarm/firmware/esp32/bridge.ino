/*
 * BAURSAK ARM — ESP32 Serial-to-PWM Bridge
 * 
 * Role: Receives servo commands via Serial (from Raspberry Pi)
 *       and drives PCA9685 PWM module to control 7 servo channels.
 * 
 * Protocol:
 *   W c1 c2 c3 c4 c5 c6 c7  — Write all 7 channels (space-separated angles)
 *   I ch angle                — Write single channel instantly
 *   H                        — Heartbeat (responds "K")
 * 
 * Channel Configuration:
 *   CH1: MG90S  gripper      [80, 180]
 *   CH2: MG90S  wrist tilt   [0, 180]
 *   CH3: MG90S  wrist rot    [0, 180]
 *   CH4: MG996R elbow        [0, 180]
 *   CH5: MG996R shoulder A   [auto: 180 - CH6]
 *   CH6: MG996R shoulder B   [0, 180]
 *   CH7: MG996R base         [-30, 220]
 * 
 * Wiring:
 *   ESP32 GPIO21 → PCA9685 SDA
 *   ESP32 GPIO22 → PCA9685 SCL
 *   ESP32 3.3V   → PCA9685 VCC (logic)
 *   ESP32 GND    → PCA9685 GND → PSU GND (common ground!)
 *   PSU 6V       → Servo VCC (red wires)
 *   PCA9685 CH1–CH7 → Servo signal (orange wires)
 * 
 * Author: Dastan Tolkynov, SDU University
 */

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pca = Adafruit_PWMServoDriver(0x40);

// PWM pulse range for servos at 50Hz (20ms period)
// 102 ≈ 0.5ms (0°), 512 ≈ 2.5ms (180°)
#define SMIN 102
#define SMAX 512

// Channel limits: index 0 unused, 1-7 = CH1-CH7
const int CH_LIMIT_MIN[] = {0,  80,   0,   0,   0,   0,   0, -30};
const int CH_LIMIT_MAX[] = {0, 180, 180, 180, 180, 180, 180, 220};

// Last known positions for diagnostics
int lastPos[8] = {0, 90, 90, 90, 90, 90, 90, 90};

/**
 * Clamp angle to channel-specific limits and write PWM pulse.
 * 
 * For standard 0-180 range: pulse = SMIN + angle * (SMAX-SMIN) / 180
 * For extended range (CH7 -30 to 220): formula extrapolates linearly
 * beyond SMIN/SMAX, producing sub-0.5ms or super-2.5ms pulses
 * that push the servo past its normal endpoints.
 */
void setServo(int ch, int angle) {
    if (ch < 1 || ch > 7) return;

    // Clamp to per-channel limits
    if (angle < CH_LIMIT_MIN[ch]) angle = CH_LIMIT_MIN[ch];
    if (angle > CH_LIMIT_MAX[ch]) angle = CH_LIMIT_MAX[ch];

    // Linear interpolation: handles negative and >180 correctly
    // Using long to prevent integer overflow on multiplication
    int pulse = SMIN + (long)(angle) * (SMAX - SMIN) / 180;

    // Safety: absolute PWM bounds (don't damage servo)
    if (pulse < 50)  pulse = 50;
    if (pulse > 600) pulse = 600;

    pca.setPWM(ch, 0, pulse);
    lastPos[ch] = angle;
}

/**
 * Parse space-separated integers from a String.
 * Returns count of parsed values.
 */
int parseInts(const String& line, int startIdx, int* out, int maxCount) {
    int count = 0;
    int si = startIdx;
    int len = line.length();

    for (int j = startIdx; j <= len && count < maxCount; j++) {
        if (j == len || line[j] == ' ') {
            if (j > si) {
                out[count++] = line.substring(si, j).toInt();
            }
            si = j + 1;
        }
    }
    return count;
}

void setup() {
    Serial.begin(115200);

    // Initialize I2C on ESP32 default pins
    Wire.begin(21, 22);

    // Initialize PCA9685
    pca.begin();
    pca.setPWMFreq(50);  // 50Hz for servo control
    delay(10);

    // All channels off — no movement on startup
    // Servos stay wherever they are until first command
    for (int i = 0; i < 16; i++) {
        pca.setPWM(i, 0, 0);
    }

    delay(200);
    Serial.println("READY");
}

void loop() {
    if (!Serial.available()) return;

    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line.length() == 0) return;

    char cmd = line[0];

    switch (cmd) {
        case 'W': {
            // Write all 7 channels: "W 90 100 90 6 80 100 120"
            int v[7];
            int count = parseInts(line, 2, v, 7);
            if (count == 7) {
                for (int i = 0; i < 7; i++) {
                    setServo(i + 1, v[i]);
                }
            }
            Serial.println("K");
            break;
        }

        case 'I': {
            // Instant single channel: "I 7 -20"
            int v[2];
            int count = parseInts(line, 2, v, 2);
            if (count == 2) {
                setServo(v[0], v[1]);
            }
            Serial.println("K");
            break;
        }

        case 'H': {
            // Heartbeat
            Serial.println("K");
            break;
        }

        case 'Q': {
            // Query positions: returns "90 100 90 6 80 100 120"
            for (int i = 1; i <= 7; i++) {
                Serial.print(lastPos[i]);
                if (i < 7) Serial.print(' ');
            }
            Serial.println();
            break;
        }

        default: {
            Serial.println("E");  // Error: unknown command
            break;
        }
    }
}
