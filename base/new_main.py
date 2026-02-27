# file: main.py
#
# Before running this read the README.md file to understand the logic flow

# Top-level loop:
#   - Open ESP32/UGV UART.Start receiving all sensor readings via ESP32. eg. wheel encoders, imu.
#   - Request fast telemetry.
#   - Repeatedly run behaviour cycles until Ctrl+C.

import json
import time
import serial

from motion import stop
from approach import do_one_cycle
from lidar_util import (
    get_front_distance_once,
    FRONT_BEARING_DEG,
    FRONT_WINDOW_DEG,
    DETECTION_RANGE_MM,
)


PORT_UGV = "/dev/ttyACM0" # connected port, do not change here
BAUD_UGV = 115200 # connected port, do not change here

def main(stop_event, ser):
    # Request fast telemetry if firmware supports T=142, cmd=50
    print("starting auto")
    ser.write((json.dumps({"T": 142, "cmd": 50}) + "\n").encode("utf-8"))
    print(f"[MAIN] Connected to UGV on {PORT_UGV} @ {BAUD_UGV}.")

    try:
        d0 = get_front_distance_once(
            target_bearing_deg=FRONT_BEARING_DEG,
            window_deg=FRONT_WINDOW_DEG,
            max_range_mm=DETECTION_RANGE_MM,
        )

    except KeyboardInterrupt:
        print("\n[MAIN] Ctrl+C received, stopping.")

    finally:
        try:
            stop(ser)
        except Exception:
            pass
        stop_event.clear()
        print("[MAIN] Serial closed, exiting.")

if __name__ == "__main__":
    ser = serial.Serial(PORT_UGV, BAUD_UGV, timeout=0.02) # connect to ports
    stop_event = False
    main(stop_event, ser)
    main()
