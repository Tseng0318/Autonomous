# file: approach.py
#
# One full cycle:
#   1) One-shot LiDAR scan to get front distance.
#   2) Approach and stop SAFETY_STOP_MM before object.
#   3) Rotate random 90 (LEFT or RIGHT).
#   4) Drive forward STEP_FORWARD_MM.
#   5) Rotate AGAIN in the SAME direction as step (3).
#   6) One-shot LiDAR scan again.


'''
Scan for obsticles --> Scan for rust --> Move forward set mm --> repeat

'''

from lidar_util import (
    get_front_distance_once,
    FRONT_BEARING_DEG,
    FRONT_WINDOW_DEG,
    DETECTION_RANGE_MM,
)

from motion import drive_forward_mm
from new_rotation import rotate_random_90, rotate_same_90
from model import detect_rust
import numpy as np 
import threading


from app.servo_final import generic_spray
# Note: app.app is imported inside do_one_cycle to avoid circular import at module load time

#TODO: Import AI and servo functions

SAFETY_STOP_MM  = 150.0   # stop 15 cm in front of detected object (not exactly accurate here)
STEP_FORWARD_MM = 50.0    # forward step after turning (5 cm)
STEP_FORWARD_DEFAULT_MM = 100.0  #Depends on camera fov

def do_one_cycle(ser) -> None:
    """
    Perform a single behaviour cycle using LiDAR + odometry.
    """
    import app.app as _app  # deferred import — avoids circular import at module load time

    print("\n=== NEW CYCLE Start ===")

    # 1) Measure front distance 
    d0 = get_front_distance_once(
        target_bearing_deg=FRONT_BEARING_DEG,
        window_deg=FRONT_WINDOW_DEG,
        max_range_mm=DETECTION_RANGE_MM,
    )
    print(f"[CYCLE] Initial front distance = {d0} mm")

    _lbl, _conf, _probs = detect_rust()
    with _app.AI_LOCK:
        _app.label = _lbl
        _app.conf  = _conf
        _app.probs = _probs
        _app.AI_CHANGED.set()  # Signal that AI results are updated

    # 2) Check if obsticle, initiate rotation logic
    approach_mm = max(0.0, float(d0))
    if approach_mm <= SAFETY_STOP_MM:
        print(f"[CYCLE] Already within {SAFETY_STOP_MM:.0f} mm; stop approach motion.")
        # 3) Rotate random 90 
        rot_dir = rotate_random_90(ser)

        # 4) Drive forward STEP_FORWARD_MM
        #print(f"[CYCLE] Driving extra {STEP_FORWARD_MM:.0f} mm.")
        drive_forward_mm(ser, STEP_FORWARD_MM, label="step")

        # 5) Rotate same direction as first rotation
        rotate_same_90(ser, rot_dir)

    # 6) Spray if rust detected
    elif _lbl == "CORROSION":  #TODO AI FUNCTION: Takes picture, looks for rust
        # Spray and then move forward
        print("[Cycle] Rust Detected: Initiating servo movement")
        generic_spray()    #TODO SERVO FUNCTION: Moves servo, activates spray
        drive_forward_mm(ser,STEP_FORWARD_DEFAULT_MM, label="step")

    else:
        # 7) If there is no obsticle, keep move set mm
        print(f"[CYCLE] Approaching ~{approach_mm:.0f} mm to stop at {SAFETY_STOP_MM:.0f} mm.")
        #TODO: Drive Forward using timed Move function
        drive_forward_mm(ser, STEP_FORWARD_DEFAULT_MM, label="step")

    
