"""
BAURSAK ARM — Built-in Sequences (V1–V10)

Each mode represents a different approach strategy for picking up
a baursak and delivering it to a human hand.

Sequence flow:
  INIT → [approach] → READY → (GRAB_WAIT) → GRAB → LIFT → DELIVER → RELEASE → INIT
"""

import time
from config import POSE_PAUSE as D, GRAB_WAIT
from poses import INIT, HIGH, READY, GRAB, LIFT, DELIVER, RELEASE


def end_seq(mc):
    """Common ending: lift → deliver → release → home."""
    mc.smooth_move(LIFT);    time.sleep(D)
    mc.smooth_move(DELIVER); time.sleep(D)
    mc.smooth_move(RELEASE); time.sleep(0.8)
    mc.smooth_move(INIT);    time.sleep(D)
    mc.finish_sequence()


def run_v(mc, n: int):
    """Execute built-in mode V1–V10."""
    with mc.lock:
        mc.sequence_running = True

    GW = GRAB_WAIT

    if n == 1:
        # Direct approach
        mc.smooth_move(READY)
        time.sleep(GW)
        mc.smooth_move(GRAB)
        time.sleep(D)
        end_seq(mc)

    elif n == 2:
        # High approach then descend
        mc.smooth_move(HIGH);  time.sleep(D)
        mc.smooth_move(READY); time.sleep(GW)
        mc.smooth_move(GRAB);  time.sleep(D)
        end_seq(mc)

    elif n == 3:
        # Rotate base first, high approach, descend
        mc.smooth_move_single(7, 0); time.sleep(D)
        mc.smooth_move(HIGH);        time.sleep(D)
        mc.smooth_move(READY);       time.sleep(GW)
        mc.smooth_move(GRAB);        time.sleep(D)
        end_seq(mc)

    elif n == 4:
        # Rotate base, direct descend
        mc.smooth_move_single(7, 0); time.sleep(D)
        mc.smooth_move(READY);       time.sleep(GW)
        mc.smooth_move(GRAB);        time.sleep(D)
        end_seq(mc)

    elif n == 5:
        # Lift arm high, rotate, descend
        mc.smooth_move([90, 90, 150, 6, 0, 100, 0]); time.sleep(D)
        mc.smooth_move(HIGH);  time.sleep(D)
        mc.smooth_move(READY); time.sleep(GW)
        mc.smooth_move(GRAB);  time.sleep(D)
        end_seq(mc)

    elif n == 6:
        # Open gripper wide, rotate, high approach
        mc.smooth_move_single(6, 32); time.sleep(D)
        mc.smooth_move_single(7, 0);  time.sleep(D)
        mc.smooth_move(HIGH);         time.sleep(D)
        mc.smooth_move(READY);        time.sleep(GW)
        mc.smooth_move(GRAB);         time.sleep(D)
        end_seq(mc)

    elif n == 7:
        # Rotate, raise individual joints, descend
        mc.smooth_move_single(7, 0);   time.sleep(D)
        mc.smooth_move_single(3, 140); time.sleep(D)
        mc.smooth_move_single(4, 80);  time.sleep(D)
        mc.smooth_move(READY);         time.sleep(GW)
        mc.smooth_move(GRAB);          time.sleep(D)
        end_seq(mc)

    elif n == 8:
        # All servos one by one to ready position
        for ch, t in [(7, 0), (6, 40), (4, 90), (3, 130), (2, 90), (1, 95)]:
            mc.smooth_move_single(ch, t)
            time.sleep(0.1)
        time.sleep(GW)
        mc.smooth_move(GRAB); time.sleep(D)
        end_seq(mc)

    elif n == 9:
        # Safe arc approach
        mc.smooth_move([90, 90, 160, 30, 0, 60, 0]); time.sleep(D)
        mc.smooth_move(HIGH);  time.sleep(D)
        mc.smooth_move(READY); time.sleep(GW)
        mc.smooth_move(GRAB);  time.sleep(D)
        end_seq(mc)

    elif n == 10:
        # Rotate, high, slow single-channel grab
        mc.smooth_move_single(7, 0); time.sleep(D)
        mc.smooth_move(HIGH);        time.sleep(D)
        mc.smooth_move(READY);       time.sleep(GW)
        mc.smooth_move_single(1, 170); time.sleep(D)
        end_seq(mc)
