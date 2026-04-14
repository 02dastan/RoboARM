"""
BAURSAK ARM — Mode Storage & Logging

Handles persistence of custom modes to JSON and
audit logging of all mode operations to text file.
"""

import json
import os
from datetime import datetime
from config import SAVED_FILE, LOG_FILE


def load_saved_modes() -> list:
    """Load saved modes from JSON file."""
    if os.path.exists(SAVED_FILE):
        try:
            with open(SAVED_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_modes_to_file(modes: list):
    """Persist modes list to JSON file."""
    with open(SAVED_FILE, "w") as f:
        json.dump(modes, f, indent=2)


def log_mode(mode_data: dict, action: str = "SAVED"):
    """
    Append human-readable log entry for mode operation.
    Format:
      ============================================================
      [2025-04-12 14:30:00] SAVED
      Name: my_custom_mode
        Pose 1: CH1=90 CH2=90 CH3=130 ... speed=60 mode=par
        Pose 2: ...
      ============================================================
    """
    with open(LOG_FILE, "a") as f:
        sep = "=" * 60
        f.write(f"\n{sep}\n")
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {action}\n")
        f.write(f"Name: {mode_data.get('name', 'unnamed')}\n")

        for i, p in enumerate(mode_data.get("poses", [])):
            mode_str = "seq" if p.get("mode", "p") == "s" else "par"
            f.write(
                f"  Pose {i+1}: "
                f"CH1={p.get('c1', 90)} "
                f"CH2={p.get('c2', 90)} "
                f"CH3={p.get('c3', 90)} "
                f"CH4={p.get('c4', 90)} "
                f"CH5+6={p.get('c6', 90)} "
                f"CH7={p.get('c7', 90)} "
                f"speed={p.get('speed', 60)} "
                f"mode={mode_str}\n"
            )
        f.write(f"{sep}\n")
