# file: rotation.py
#
# 90 degree rotation using odl/odr (scaled to mm by motion.py)

import time
import math
import random

from motion import read_odl_odr, send_cmd, stop


# CONFIG
WHEEL_BASE_MM   = 160.0    # distance between wheels [mm], not exact
ANG_SPEED_RPS   = 1.0      # yaw rate command [rad/s]
POLL_DT         = 0.02
PROGRESS_EVERY  = 0.2

# NOTE:
# should be set to 90, but would causes ~180° rotation, so hard code it 
TARGET_DEG = 22.5


# CORE ROTATION
def rotate_90(ser, direction: int, target_deg: float = TARGET_DEG) -> None:
    """
    Rotate approximately target_deg in the given direction.
      direction = +1  -> LEFT
      direction = -1  -> RIGHT
    """
    if direction not in (-1, +1):
        raise ValueError("direction must be +1 (LEFT) or -1 (RIGHT)")

    print("[ROT] Turning LEFT" if direction > 0 else "[ROT] Turning RIGHT")

    # Baseline odometry
    L0 = R0 = None
    while L0 is None or R0 is None:
        L0, R0 = read_odl_odr(ser, 1.0)

    # Command yaw only
    send_cmd(ser, 0.0, ANG_SPEED_RPS * direction)

    start = time.monotonic()
    last_print = start

    try:
        while True:
            time.sleep(POLL_DT)

            L, R = read_odl_odr(ser, 0.2)
            if L is None or R is None:
                continue

            dL = L - L0
            dR = R - R0

            # Differential-drive heading estimate
            theta_rad = (dR - dL) / WHEEL_BASE_MM
            theta_deg_signed = math.degrees(theta_rad)

            # Progress toward commanded direction
            theta_progress = theta_deg_signed * direction

            now = time.monotonic()
            if now - last_print >= PROGRESS_EVERY:
                print(f"[ROT] θ≈{theta_progress:.1f}°  (ΔL={dL:+d}, ΔR={dR:+d})")
                last_print = now

            if theta_progress >= target_deg:
                print(f"[ROT] Target {target_deg:.1f}° reached.")
                break

            if now - start > 10.0:
                print("[ROT] WARNING: rotation timeout; stopping.")
                break

    finally:
        stop(ser)


# PUBLIC API
def rotate_random_90(ser, target_deg: float = TARGET_DEG) -> int:
    """
    Rotate in a random direction and RETURN the direction.
    Returns:
      +1 for LEFT
      -1 for RIGHT
    """
    direction = random.choice([-1, +1])
    rotate_90(ser, direction, target_deg)
    return direction


def rotate_same_90(ser, direction: int, target_deg: float = TARGET_DEG) -> None:
    """
    Rotate again in the SAME direction as a previous rotation.
    Use the direction returned by rotate_random_90().
    """
    rotate_90(ser, direction, target_deg)