"""
BAURSAK ARM — Motion Controller

Handles all servo movement: smooth easing, manual control,
sequence execution, and paired channel mirroring.

Architecture:
  - Background thread runs at TICK_HZ, interpolating manual targets
  - Sequence moves computed on Pi with easing, sent to ESP32 at TICK_HZ
  - CH5 always mirrors CH6: CH5 = 180 - CH6
"""

import time
import math
import threading
import serial
from config import (
    SERIAL_PORT, SERIAL_BAUD, TICK_HZ,
    MIN_DURATION, MAX_DURATION, DEG_PER_SEC, clamp_ch
)


# =============================================================
#  Serial Communication
# =============================================================
ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1)
time.sleep(2)
ser.reset_input_buffer()
_ser_lock = threading.Lock()


def raw_write_all(positions: list):
    """Send all 7 servo positions to ESP32. Format: W c1 c2 ... c7"""
    cmd = "W " + " ".join(str(int(p)) for p in positions) + "\n"
    with _ser_lock:
        ser.write(cmd.encode())
        ser.reset_input_buffer()


def raw_write_single(ch: int, angle: float):
    """Send single channel position. Format: I ch angle"""
    cmd = f"I {ch} {int(angle)}\n"
    with _ser_lock:
        ser.write(cmd.encode())
        ser.reset_input_buffer()


# =============================================================
#  Easing Functions
# =============================================================
def ease_in_out_cubic(t: float) -> float:
    """Smooth S-curve with acceleration and deceleration."""
    if t < 0.5:
        return 4 * t * t * t
    return 1 - pow(-2 * t + 2, 3) / 2


# =============================================================
#  Motion Controller
# =============================================================
class MotionController:
    """
    Central servo motion manager.

    Two operating modes:
    1. Manual: background thread smoothly moves servos toward manual_target
    2. Sequence: smooth_move() takes full control, background thread yields

    Thread safety via self.lock for all shared state access.
    """

    def __init__(self):
        self.current = [90.0] * 7         # Actual servo positions
        self.manual_target = [90.0] * 7   # Targets for manual mode
        self.sequence_running = False
        self.lock = threading.Lock()

        # Background thread for manual mode smoothing
        self._thread = threading.Thread(target=self._manual_loop, daemon=True)
        self._thread.start()

    # ---------------------------------------------------------
    #  Internal helpers
    # ---------------------------------------------------------
    def _apply_pair(self, positions: list) -> list:
        """Apply CH5 = 180 - CH6 mirroring."""
        p = list(positions)
        p[4] = 180.0 - p[5]
        return p

    def _send(self, positions: list):
        """Send positions with pairing applied."""
        raw_write_all(self._apply_pair(positions))

    def _manual_loop(self):
        """
        Background loop: smoothly moves servos toward manual targets.
        Only active when no sequence is running.
        Speed scales with distance for natural feel.
        """
        interval = 1.0 / TICK_HZ
        while True:
            t0 = time.monotonic()
            with self.lock:
                if not self.sequence_running:
                    changed = False
                    for i in range(7):
                        diff = self.manual_target[i] - self.current[i]
                        if abs(diff) < 0.5:
                            if self.current[i] != self.manual_target[i]:
                                self.current[i] = self.manual_target[i]
                                changed = True
                            continue
                        dist = abs(diff)
                        # Adaptive speed: slow for precision, fast for big moves
                        if dist < 5:
                            speed = 0.5
                        elif dist < 20:
                            speed = 1.5
                        elif dist < 60:
                            speed = 3.0
                        else:
                            speed = 4.0
                        step = min(speed, dist)
                        self.current[i] += step if diff > 0 else -step
                        changed = True
                    if changed:
                        self._send(self.current)
            sleep_t = interval - (time.monotonic() - t0)
            if sleep_t > 0:
                time.sleep(sleep_t)

    # ---------------------------------------------------------
    #  Manual control API
    # ---------------------------------------------------------
    def set_manual(self, ch: int, angle: int):
        """Set manual target for one channel (1-7)."""
        angle = clamp_ch(ch, angle)
        with self.lock:
            self.manual_target[ch - 1] = float(angle)
            if ch == 6:
                self.manual_target[4] = 180.0 - float(angle)

    def set_manual_pair(self, angle: int):
        """Set CH5+6 pair target."""
        angle = max(0, min(180, angle))
        with self.lock:
            self.manual_target[5] = float(angle)
            self.manual_target[4] = 180.0 - float(angle)

    # ---------------------------------------------------------
    #  Sequence control
    # ---------------------------------------------------------
    def _calc_duration(self, start: list, end: list, speed=None) -> float:
        """Calculate move duration from max channel distance."""
        spd = speed or DEG_PER_SEC
        max_dist = max(
            abs(end[i] - start[i]) for i in range(7) if i != 4
        )
        if max_dist == 0:
            return 0.1
        return max(MIN_DURATION, min(MAX_DURATION, max_dist / spd))

    def smooth_move(self, target: list, easing=ease_in_out_cubic,
                    duration=None, speed=None):
        """
        Move all servos smoothly using easing interpolation.
        Computed on Pi, raw positions sent at TICK_HZ.
        """
        with self.lock:
            self.sequence_running = True
            start_pos = list(self.current)

        target = [clamp_ch(i + 1, target[i]) if i != 4 else target[i]
                  for i in range(7)]

        if duration is None:
            duration = self._calc_duration(start_pos, target, speed)

        steps = max(1, int(duration * TICK_HZ))
        for s in range(steps + 1):
            e = easing(s / steps)
            pos = [
                start_pos[i] + (target[i] - start_pos[i]) * e
                if i != 4 else 0
                for i in range(7)
            ]
            pos[4] = 180.0 - pos[5]
            raw_write_all(pos)
            with self.lock:
                self.current = list(pos)
            time.sleep(1.0 / TICK_HZ)

        with self.lock:
            self.current = list(target)
            self.current[4] = 180.0 - self.current[5]

    def smooth_move_single(self, ch: int, target_angle,
                           easing=ease_in_out_cubic, speed=None):
        """Move single channel smoothly."""
        target_angle = clamp_ch(ch, target_angle)
        spd = speed or DEG_PER_SEC

        with self.lock:
            self.sequence_running = True
            start = self.current[ch - 1]

        dist = abs(target_angle - start)
        if dist < 1:
            return

        duration = max(MIN_DURATION, min(MAX_DURATION, dist / spd))
        steps = max(1, int(duration * TICK_HZ))

        for s in range(steps + 1):
            angle = start + (target_angle - start) * easing(s / steps)
            if ch == 6:
                raw_write_single(6, angle)
                raw_write_single(5, 180 - angle)
                with self.lock:
                    self.current[5] = angle
                    self.current[4] = 180 - angle
            else:
                raw_write_single(ch, angle)
                with self.lock:
                    self.current[ch - 1] = angle
            time.sleep(1.0 / TICK_HZ)

    def run_pose(self, pose: list, mode="parallel", speed=None):
        """Execute single pose with given mode."""
        if mode == "sequential":
            for i in range(7):
                if i == 4:
                    continue
                self.smooth_move_single(i + 1, pose[i], speed=speed)
                time.sleep(0.05)
        else:
            self.smooth_move(pose, speed=speed)

    def finish_sequence(self):
        """Mark sequence complete, sync manual targets to current pos."""
        with self.lock:
            self.sequence_running = False
            self.manual_target = list(self.current)

    def init_pose(self, pose: list):
        """Set initial position directly (first startup)."""
        with self.lock:
            self.current = list(pose)
            self.manual_target = list(pose)
            self.current[4] = 180.0 - self.current[5]
            self.manual_target[4] = 180.0 - self.manual_target[5]
        self._send(self.current)

    def get_positions(self) -> dict:
        """Return current positions as dict for API."""
        with self.lock:
            c = self.current
        return {
            1: int(c[0]), 2: int(c[1]), 3: int(c[2]),
            4: int(c[3]), 6: int(c[5]), 7: int(c[6])
        }
