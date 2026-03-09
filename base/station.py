#!/usr/bin/env python3
# file: pattern_square.py
#
# Standalone pattern driver (no changes to existing modules):
#   Forward 10 cm -> Rotate RIGHT -> repeat

import json
import time
import serial

from motion import drive_forward_mm, stop
from new_rotation import rotate_90  # uses your existing function: direction=-1 means RIGHT
from model import detect_rust

PORT_UGV = "/dev/ttyACM0"
BAUD_UGV = 115200

STEP_MM = 4572.0        # 50 cm
N_REPS = 20            # number of repetitions; set to None for infinite loop
PAUSE_S = 0.05         # small pause between actions


def request_fast_telemetry(ser) -> None:
    """Ask MCU to stream telemetry faster (same as your main.py)."""
    ser.write((json.dumps({"T": 142, "cmd": 50}) + "\n").encode("utf-8"))


def run_pattern(ser, step_mm: float = STEP_MM, reps: int | None = N_REPS) -> None:
    i = 0
    while True:
        i += 1
        print(f"\n=== PATTERN REP {i} ===")

        print(f"[PATTERN] Forward {step_mm:.0f} mm")
        drive_forward_mm(ser, step_mm, label=f"fwd_{i}")
        time.sleep(PAUSE_S)
        detect_rust()
        print("[PATTERN] Rotate RIGHT (~90 using your current rotation tuning)")
        rotate_90(ser, direction=1)  # RIGHT
        time.sleep(PAUSE_S)

        if reps is not None and i >= reps:
            print("\n[PATTERN] Completed requested repetitions.")
            break


def main():
    ser = None
    try:
        ser = serial.Serial(PORT_UGV, BAUD_UGV, timeout=0.02)
        time.sleep(0.03)

        request_fast_telemetry(ser)
        try:
            ser.reset_input_buffer()
        except Exception:
            pass

        print(f"[MAIN] Connected to UGV on {PORT_UGV} @ {BAUD_UGV}")
        print("Press Ctrl+C to stop.\n")

        run_pattern(ser)


    except KeyboardInterrupt:
        print("\n[MAIN] Ctrl+C received, stopping.")
    finally:
        if ser is not None:
            try:
                stop(ser)
            except Exception:
                pass
            try:
                ser.close()
            except Exception:
                pass
        print("[MAIN] Serial closed, exiting.")


if __name__ == "__main__":
    main()
