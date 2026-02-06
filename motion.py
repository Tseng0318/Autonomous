# file: motion.py
#
# Forward motion using odl/odr in mm from the ESP32 firmware.

import json
import time

FORWARD_SPEED_DEFAULT = 0.15   # magnitude of speed [m/s]
POLL_DT_DEFAULT       = 0.05   # s
PROGRESS_EVERY        = 0.5    # s

# IMPORTANT:
# X>0 moves it in the opposite direction from where the LiDAR is facing.

FORWARD_SIGN = -1.0            # necessary to flip the direction

def send_cmd(ser, x: float, z: float = 0.0) -> None:
    """Send velocity command (X forward [m/s], Z yaw [rad/s])."""
    msg = {"T": 13, "X": float(x), "Z": float(z)}
    ser.write((json.dumps(msg) + "\n").encode("utf-8"))

def stop(ser) -> None:
    send_cmd(ser, 0.0, 0.0)

def read_odl_odr(ser, wait_s: float = 0.5):
    """
    Read one telemetry line containing odl/odr (in mm).
    Returns (odl_mm, odr_mm) or (None, None) if timeout.
    """
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and ("odl" in obj) and ("odr" in obj):
            try:
                return int(obj["odl"]), int(obj["odr"])
            except Exception:
                continue
    return None, None

def drive_forward_mm(
    ser,
    distance_mm: float,
    speed_mps: float = FORWARD_SPEED_DEFAULT,
    timeout_s: float = 25.0,
    poll_dt: float = POLL_DT_DEFAULT,
    label: str = "forward"
) -> None:
    """
    Drive "forward" by distance_mm, where forward means toward the LiDAR-facing direction.
    
    Uses odl/odr telemetry in mm. Blocks until done or timeout.
    """
    target_mm = max(0.0, float(distance_mm))
    if target_mm <= 1.0:
        print(f"[MOTION] Requested {label} distance {target_mm:.1f} mm; skipping.")
        return

    # Baseline odometry
    L0 = R0 = None
    while L0 is None or R0 is None:
        L0, R0 = read_odl_odr(ser, 1.0)
    print(f"[MOTION] Baseline odl/odr: {L0} / {R0} ({label})")

    # Apply sign so that "forward" in our code moves toward the object.
    commanded_speed = FORWARD_SIGN * speed_mps
    send_cmd(ser, commanded_speed, 0.0)

    start = time.monotonic()
    last_print = start
    last_L, last_R = L0, R0

    try:
        while True:
            time.sleep(poll_dt)
            L, R = read_odl_odr(ser, 0.2)
            if L is not None and R is not None:
                dL = (L - L0)*10
                dR = (R - R0)*10
                avg_mm = 0.5 * (abs(dL) + abs(dR))

                now = time.monotonic()
                if now - last_print >= PROGRESS_EVERY:
                    print(f"[PROG {label}] avg_mm={avg_mm:.0f} / {target_mm:.0f}  (ΔL={L-last_L:+d}, ΔR={R-last_R:+d})")
                    last_print = now
                    last_L, last_R = L, R

                if avg_mm >= target_mm:
                    print(f"[MOTION] Stop {label}: avg_mm={avg_mm:.0f} ≥ target_mm={target_mm:.0f}.")
                    break

            if time.monotonic() - start > timeout_s:
                print(f"[MOTION] WARNING: timeout during {label}; stopping.")
                break

    finally:
        stop(ser)
