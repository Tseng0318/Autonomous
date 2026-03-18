import json
import math
import time

from motion import send_cmd, stop

POLL_DT = 0.03
TURN_KP = 0.035
MAX_Z = 1.0
MIN_Z = 0.18
ANGLE_TOL_DEG = 2.0
TIMEOUT_S = 6.0


def wrap_deg(angle):
    """Wrap angle to [-180, 180)."""
    return (angle + 180.0) % 360.0 - 180.0


def clamp(val, lo, hi):
    return max(lo, min(hi, val))


def read_latest_imu_yaw(ser, wait_s=0.05):
    """
    Read latest telemetry line that contains IMU yaw.
    Adjust the key name after you inspect your actual ESP32 JSON.
    Common possibilities: 'yaw', 'gz', 'imu_yaw', etc.
    """
    deadline = time.monotonic() + wait_s
    latest_yaw = None

    while time.monotonic() < deadline:
        if ser.in_waiting <= 0:
            continue

        raw = ser.readline()
        if not raw:
            continue

        try:
            obj = json.loads(raw.decode("utf-8", errors="ignore").strip())
        except json.JSONDecodeError:
            continue

        if not isinstance(obj, dict):
            continue

        # CHANGE THIS after checking your actual telemetry fields
        if "yaw" in obj:
            try:
                latest_yaw = float(obj["yaw"])
            except (TypeError, ValueError):
                pass

    return latest_yaw


def turn_to_relative_angle(ser, delta_deg):
    """
    Turn by a relative angle.
    delta_deg > 0 => left turn
    delta_deg < 0 => right turn
    """
    y0 = None
    while y0 is None:
        y0 = read_latest_imu_yaw(ser, wait_s=0.2)

    target_yaw = wrap_deg(y0 + delta_deg)
    print(f"[IMU ROT] start={y0:.1f}°, target={target_yaw:.1f}°")

    start_t = time.monotonic()

    try:
        while True:
            yaw = read_latest_imu_yaw(ser, wait_s=0.1)
            if yaw is None:
                continue

            error = wrap_deg(target_yaw - yaw)

            if abs(error) <= ANGLE_TOL_DEG:
                print(f"[IMU ROT] done, yaw={yaw:.1f}°, error={error:.1f}°")
                break

            z = TURN_KP * error
            z = clamp(z, -MAX_Z, MAX_Z)

            if 0 < abs(z) < MIN_Z:
                z = math.copysign(MIN_Z, z)

            send_cmd(ser, 0.0, z)

            print(f"[IMU ROT] yaw={yaw:.1f}°, error={error:.1f}°, z={z:.2f}")
            time.sleep(POLL_DT)

            if time.monotonic() - start_t > TIMEOUT_S:
                print("[IMU ROT] timeout")
                break

    finally:
        stop(ser)
