# file: approach.py
#
# One full cycle:
#   1) One-shot LiDAR scan to get front distance.
#   2) Approach and stop SAFETY_STOP_MM before object.
#   3) Rotate random 90 (LEFT or RIGHT).
#   4) Drive forward STEP_FORWARD_MM.
#   5) Rotate AGAIN in the SAME direction as step (3).
#   6) One-shot LiDAR scan again.

from lidar_util import (
    get_front_distance_once,
    FRONT_BEARING_DEG,
    FRONT_WINDOW_DEG,
    DETECTION_RANGE_MM,
)

from motion import drive_forward_mm
from new_rotation import rotate_random_90, rotate_same_90

SAFETY_STOP_MM  = 150.0   # stop 15 cm in front of detected object (not exactly accurate here)
STEP_FORWARD_MM = 50.0    # forward step after turning (5 cm)


def do_one_cycle(ser) -> None:
    """
    Perform a single behaviour cycle using LiDAR + odometry.
    """
    print("\n=== NEW CYCLE Start ===")

    # 1) Measure front distance once
    d0 = get_front_distance_once(
        target_bearing_deg=FRONT_BEARING_DEG,
        window_deg=FRONT_WINDOW_DEG,
        max_range_mm=DETECTION_RANGE_MM,
    )
    print(f"[CYCLE] Initial front distance = {d0} mm")

    # 2) Approach and stop SAFETY_STOP_MM before object
    approach_mm = max(0.0, float(d0) - SAFETY_STOP_MM)
    if approach_mm <= 5.0:
        print(f"[CYCLE] Already within {SAFETY_STOP_MM:.0f} mm; stop approach motion.")
    else:
        print(f"[CYCLE] Approaching ~{approach_mm:.0f} mm to stop at {SAFETY_STOP_MM:.0f} mm.")
        drive_forward_mm(ser, approach_mm, label="approach")

    # 3) Rotate random 90 and CAPTURE direction
    rot_dir = rotate_random_90(ser)

    # 4) Drive forward STEP_FORWARD_MM
    print(f"[CYCLE] Driving extra {STEP_FORWARD_MM:.0f} mm.")
    drive_forward_mm(ser, STEP_FORWARD_MM, label="step")

    # 5) Rotate same direction as first rotation
    rotate_same_90(ser, rot_dir)

    # 6) Scan again for information
    d1 = get_front_distance_once(
        target_bearing_deg=FRONT_BEARING_DEG,
        window_deg=FRONT_WINDOW_DEG,
        max_range_mm=DETECTION_RANGE_MM,
    )
    print(f"[CYCLE] New front distance = {d1} mm")
