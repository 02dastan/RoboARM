"""
BAURSAK ARM — Configuration
All tunable parameters in one place.
"""

# Serial connection to ESP32
SERIAL_PORT = "/dev/ttyUSB0"
SERIAL_BAUD = 115200

# Web server
WEB_HOST = "0.0.0.0"
WEB_PORT = 8080
PASSWORD = "baursak2024"

# Motion control
TICK_HZ = 60          # Servo update rate (Hz)
MIN_DURATION = 0.3    # Minimum move time (seconds)
MAX_DURATION = 3.0    # Maximum move time (seconds)
DEG_PER_SEC = 60      # Default speed for sequences
GRAB_WAIT = 1.0       # Pause before grabbing (seconds)
POSE_PAUSE = 0.3      # Pause between poses in sequence

# Per-channel angle limits [index 0 unused, 1-7 = CH1-CH7]
CH_MIN = [0, 80, 0, 0, 0, 0, 0, -30]
CH_MAX = [0, 180, 180, 180, 180, 180, 180, 220]

# Storage
SAVED_FILE = "saved_modes.json"
LOG_FILE = "modes_log.txt"


def clamp_ch(ch: int, angle) -> int:
    """Clamp angle to channel-specific limits."""
    return max(CH_MIN[ch], min(CH_MAX[ch], int(angle)))
