# file: lidar_util.py
#
# reads the data points from lidar within 20 degree range, so 340 to 20 degree range

import math
import statistics
import threading
from time import sleep, monotonic
from rplidar import RPLidar, RPLidarException


# BASIC CONFIG
# do not change the port
PORT = "/dev/ttyAMA0"
BAUD = 115200

DETECTION_RANGE_MM = 12000

# 0 is FRONT
FRONT_BEARING_DEG = 0.0

# Front window 
FRONT_WINDOW_DEG = 20.0

# Require enough points before trusting the median
MIN_POINTS_IN_WINDOW = 10

# How much data to collect before deciding
MAX_SCAN_BATCHES = 12
MAX_TIME_S = 2.0
MAX_DESCRIPTOR_RETRIES = 3
RETRY_BACKOFF_S = 0.25

# Reject unrealistically close junk returns
MIN_VALID_MM = 80

# Mask a tiny band around 0 ONLY if chassis causes reflections
# this is not necessary now
CHASSIS_MASK_DEG = None   # e.g. 2.0 if needed

LIDAR_SCAN_LOCK = threading.Lock()


def _ang_diff(a_deg: float, b_deg: float) -> float:
    """Smallest signed difference a-b in degrees, in [-180, 180]."""
    return (a_deg - b_deg + 180.0) % 360.0 - 180.0


def _masked(angle_deg: float, center_deg: float, half_width_deg: float) -> bool:
    return abs(_ang_diff(angle_deg, center_deg)) <= half_width_deg


def _shutdown_lidar(lidar: RPLidar | None) -> None:
    if lidar is None:
        return
    try:
        lidar.stop()
    except Exception:
        pass
    try:
        lidar.stop_motor()
    except Exception:
        pass
    try:
        lidar.disconnect()
    except Exception:
        pass



# MAIN function in this module
def get_front_distance_once(
    port: str | None = None,
    target_bearing_deg: float = FRONT_BEARING_DEG,
    window_deg: float = FRONT_WINDOW_DEG,
    max_range_mm: int = DETECTION_RANGE_MM,
    min_points: int = MIN_POINTS_IN_WINDOW,
    min_valid_mm: int = MIN_VALID_MM,
    spinup_s: float = 1.0,
    max_scan_batches: int = MAX_SCAN_BATCHES,
    max_time_s: float = MAX_TIME_S,
    chassis_mask_deg: float | None = CHASSIS_MASK_DEG,
    max_descriptor_retries: int = MAX_DESCRIPTOR_RETRIES,
    retry_backoff_s: float = RETRY_BACKOFF_S,
) -> int:
    """
    Robust front distance estimate.

    Strategy:
      - Collect multiple scans batches, so allow the lidar spin for a while
      - Use median of points within window_deg
      - Only fall back to nearest overall if absolutely necessary

    Returns:
      distance_mm (int)
    """
    dev_port = PORT if port is None else port
    last_error: Exception | None = None
    retries = max(1, int(max_descriptor_retries))

    for attempt in range(1, retries + 1):
        lidar = None
        try:
            with LIDAR_SCAN_LOCK:
                lidar = RPLidar(dev_port, baudrate=BAUD, timeout=3)
                lidar.start_motor()
                sleep(spinup_s)

                window_vals: list[float] = []
                nearest_overall: float | None = None

                t0 = monotonic()
                batches = 0

                for scan in lidar.iter_scans(min_len=5):
                    batches += 1

                    for quality, angle_deg, dist_mm in scan:
                        if not dist_mm:
                            continue

                        d = float(dist_mm)
                        if d <= min_valid_mm or d > max_range_mm:
                            continue

                        a = float(angle_deg) % 360.0

                        if nearest_overall is None or d < nearest_overall:
                            nearest_overall = d

                        if abs(_ang_diff(a, target_bearing_deg)) <= window_deg:
                            if chassis_mask_deg is not None and _masked(a, target_bearing_deg, chassis_mask_deg):
                                continue
                            window_vals.append(d)

                    if len(window_vals) >= min_points:
                        d_med = int(round(statistics.median(window_vals)))
                        print(
                            f"[LiDAR] Front @{target_bearing_deg:.1f} {window_deg:.1f} "
                            f"hits={len(window_vals)} batches={batches}  {d_med} mm"
                        )
                        return d_med

                    if batches >= max_scan_batches:
                        break
                    if (monotonic() - t0) >= max_time_s:
                        break

                if nearest_overall is not None:
                    d_fb = int(round(nearest_overall))
                    print(
                        f"[LiDAR] Not enough front hits (hits={len(window_vals)} batches={batches}); "
                        f"nearest overall = {d_fb} mm"
                    )
                    return d_fb

                raise RuntimeError("No valid LiDAR data collected.")

        except RPLidarException as e:
            last_error = e
            msg = str(e).lower()
            descriptor_error = "descriptor" in msg and "mismatch" in msg
            if descriptor_error and attempt < retries:
                print(f"[LiDAR] Descriptor mismatch, retrying ({attempt}/{retries})...")
                sleep(retry_backoff_s)
                continue
            raise RuntimeError(f"LiDAR error: {e}") from e
        finally:
            _shutdown_lidar(lidar)

    if last_error is not None:
        raise RuntimeError(f"LiDAR error after retries: {last_error}") from last_error
    raise RuntimeError("LiDAR error after retries.")
