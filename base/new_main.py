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

PORT_UGV = "/dev/ttyACM0" # connected port, do not change here
BAUD_UGV = 115200 # connected port, do not change here

def main(stop_event):
    ser = serial.Serial(PORT_UGV, BAUD_UGV, timeout=0.02) # connect to ports
    time.sleep(0.1)

    # Request fast telemetry if firmware supports T=142, cmd=50
    ser.write((json.dumps({"T": 142, "cmd": 50}) + "\n").encode("utf-8"))
    print(f"[MAIN] Connected to UGV on {PORT_UGV} @ {BAUD_UGV}.")

    try:
        while not stop_event.is_set():
            do_one_cycle(ser) # perform the preset path logic
            time.sleep(1.0)  # small pause between cycles

    except KeyboardInterrupt:
        print("\n[MAIN] Ctrl+C received, stopping.")

    finally:
        try:
            stop(ser)
        except Exception:
            pass
        ser.close()
        stop_event.clear()
        print("[MAIN] Serial closed, exiting.")

if __name__ == "__main__":
    main()
