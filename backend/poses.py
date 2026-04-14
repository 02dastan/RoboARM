"""
BAURSAK ARM — Pose Definitions

Each pose is a list of 7 values: [CH1, CH2, CH3, CH4, CH5, CH6, CH7]
CH5 is auto-mirrored (180 - CH6), so its value here is ignored.

Convention:
  Index 0 = CH1 (gripper)
  Index 1 = CH2 (wrist tilt)
  Index 2 = CH3 (wrist rotate)
  Index 3 = CH4 (elbow)
  Index 4 = CH5 (shoulder A — auto)
  Index 5 = CH6 (shoulder B — input)
  Index 6 = CH7 (base rotation)
"""

# Base position — robot idle, waiting for command
INIT    = [90, 100,  90,   6,  0, 100, 120]

# Approach from above — arm raised before descending to baursak
HIGH    = [90,  90, 140,  80,  0,  32,   0]

# At baursak — gripper open, ready to grab
READY   = [95,  90, 130,  90,  0,  40,   0]

# Grabbed — gripper closed on baursak
GRAB    = [170, 90, 130,  90,  0,  40,   0]

# Lifted — baursak raised safely above obstacles
LIFT    = [180, 90, 150,  70,  0,  90,   0]

# At human hand — extended to delivery position
DELIVER = [170, 90, 150, 100,  0,  70, 130]

# Released — gripper open, baursak dropped into hand
RELEASE = [90,  90, 150, 100,  0,  70, 130]
