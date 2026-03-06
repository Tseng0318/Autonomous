#!/usr/bin/env python3
"""
Unified robot controller for your setup:
- /move  → proxies to the BASE (Wi-Fi API)
- /servo → sends 'servoX angle' commands to the ARM 
- /valve → sends 'valve on' or 'valve off' to the ARM
"""

import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)                        # workspace root — makes 'base' importable as a package
sys.path.insert(1, os.path.join(_ROOT, 'base'))  # base/ itself — so bare imports inside base files work

from flask import Flask, request, render_template, jsonify
import os, time, glob, logging, requests, json
import threading
import numpy as np

# --- Hardware availability flag (False on Windows / non-Pi environments) ---
HARDWARE_AVAILABLE = True

import serial

from app.servo_final import set_angle, setup_servo, cleanup, valve_toggle
from base.new_main import main as auto



app = Flask(__name__, template_folder="templates")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")


# --- Base (Wi-Fi) ---
BASE_HOST        = os.getenv("BASE_HOST", "http://192.168.4.1")     # base IP
BASE_MOVE_PATH   = os.getenv("BASE_MOVE_PATH", "/move")              # base path
BASE_METHOD      = os.getenv("BASE_METHOD", "GET")                   # GET or POST
BASE_TIMEOUT_S   = float(os.getenv("BASE_TIMEOUT_S", "0.5"))
BASE_AUTH        = os.getenv("BASE_AUTH", None)                      # optional token


# --- Arm (Arduino over USB) ---
ARM_BAUD         = int(os.getenv("ARM_BAUD", "9600"))                
ARM_PORT_PATTERN = os.getenv("ARM_PORT_PATTERN", "/dev/ttyACM*")     # or /dev/ttyUSB*
REQUIRE_INDEX    = True

# Serial Setup (ARM)
PORT_UGV = "/dev/ttyACM0" # connected port, do not change here
BAUD_UGV = 115200 # connected port, do not change here

ser = serial.Serial(PORT_UGV, BAUD_UGV, timeout=0.02) # connect to ports


stop_event = threading.Event()
AUTO_MOVE = None
SCAN_THREAD_LOCK = threading.Lock()

label, conf, probs = "", 0.0, np.array([])  #For AI Model results
AI_LOCK = threading.Lock()

AI_MODEL_THREAD = None
AI_CHANGED = threading.Event()
AI_DISPLAY_STOP = threading.Event()

# --- Scan result tracking ---
scan_results = []                        # accumulated per-cycle AI results
_scan_result_lock = threading.Lock()
_STATION_NAMES = ["A", "B", "C"]
_current_station_idx = 0

def _ai_display_worker():
    """Background thread: fires every time detect_rust() produces a new result."""
    global label, conf, probs, _current_station_idx
    while not AI_DISPLAY_STOP.is_set():
        AI_CHANGED.wait()  # Block until approach.py sets the event
        with AI_LOCK:
            station = _STATION_NAMES[_current_station_idx % len(_STATION_NAMES)]
            decision = "Rust" if label == "CORROSION" else ("Clean" if conf >= 0.65 else "Uncertain")
            action   = "Spray" if label == "CORROSION" else ("None" if decision == "Clean" else "Review")
            entry = {
                "station":  station,
                "score":    round(float(conf), 4),
                "decision": decision,
                "action":   action,
                "time":     time.strftime("%H:%M:%S"),
            }
            with _scan_result_lock:
                scan_results.append(entry)
            _current_station_idx += 1
            app.logger.info(f"[DISPLAY] Station {station}: {decision} ({conf:.2%})")
            AI_CHANGED.clear()


def _run_auto_thread():
    try:
        auto(stop_event, ser)
    except Exception as e:
        app.logger.exception(f"[AUTO] Autonomous thread crashed: {e}")


def _auto_serial(pattern, baud):
    '''
    functionality: 
        Auto-detect and open a serial port.
    args:
        pattern: glob pattern to search for serial ports
        baud: baud rate for serial communication
    '''
    ports = sorted(glob.glob(pattern))
    if not ports:
        raise RuntimeError(f"No serial ports found matching {pattern}")
    s = serial.Serial(ports[0], baudrate=baud, timeout=1)
    try:
        s.setRTS(False); s.setDTR(False)
    except Exception:
        pass
    time.sleep(0.3)
    return s

def _arm_send_line(line: str):
    '''
    functionality:
        Send a text command terminated by newline.
    args:
        line: command string to send
    '''
    if ser is None or not ser.is_open:
        raise RuntimeError("Serial not initialized")
    if not line.endswith("\n"):
        line += "\n"
    ser.write(line.encode("utf-8"))
    app.logger.info(f"[ARM] → {line.strip()}")

# Base (Wi-Fi proxy)
def _base_headers():
    '''
    functionality:
        Construct headers for the base (Wi-Fi) requests.
    '''
    h = {"Accept":"application/json"}
    if BASE_AUTH: h["Authorization"]=BASE_AUTH
    return h

# Base Movement
def move_base(L,R):
    '''
    functionality:
        Move the base with left and right speeds (-1 to 1).
    args:
        L: left wheel speed
        R: right wheel speed
    '''
    if not (-1<=L<=1 and -1<=R<=1):
        raise ValueError("Speeds must be between -1 and 1")
    msg = {"T": 1, "L": L, "R": R}
    ser.write((json.dumps(msg) + "\n").encode("utf-8"))


# Arm (Servo + Valve)
def move_servo(servo_num:int, angle:int):
    '''
    functionality:
        Move a servo to a specific angle (0 to 180).
    args:
        servo_num: the servo number (1 to 4)
        angle: the angle to move to (0 to 180)
    '''
    if not (1 <= servo_num <= 4):
        raise ValueError("Servo number must be between 1 and 4")
    angle = max(0, min(180, int(angle)))
    set_angle(servo_num, angle)

def valve_control(state:str):
    '''
    functionality:
        Control the valve state ('on' or 'off').
    args:
        state: the desired state of the valve ('on' or 'off')
    '''
    state = state.lower()
    if state not in ("on", "off"):
        raise ValueError("State must be 'on' or 'off'")
    valve_toggle(state)
    #_arm_send_line(f"valve {state}")

# Flask routes
@app.route("/")
def index():
    if REQUIRE_INDEX:
        return render_template("index.html")
    return jsonify(ok=True)

@app.route("/autonomous")
def autonomous():
    try:
        return render_template("autonomous.html")
    except Exception as e:
        app.logger.exception("Autonomous page error")
        return jsonify(ok=False, error=str(e)), 500

@app.route("/display")
def display():
    try:
        return render_template("newDisplay.html")
    except Exception as e:
        app.logger.exception("Display page error")
        return jsonify(ok=False, error=str(e)), 500

@app.route("/ping")
def ping(): return jsonify(ok=True)

@app.route("/move")
def handle_move():
    if AUTO_MOVE is not None and AUTO_MOVE.is_alive():
        print("Cannot move manually while autonomous mode is active")
        return -1
    try:
        L=float(request.args.get("L",0))
        R=float(request.args.get("R",0))
        move_base(L,R)
        return jsonify(ok=True)
    except Exception as e:
        app.logger.exception("Move error")
        return jsonify(ok=False,error=str(e)),502

@app.route("/servo")
def handle_servo():
    try:
        s=int(request.args.get("servo"))
        d=float(request.args.get("degrees"))
        move_servo(s,d)
        return jsonify(ok=True)
    except Exception as e:
        app.logger.exception("Servo error")
        return jsonify(ok=False,error=str(e)),400

@app.route("/valve")
def handle_valve():
    try:
        state=request.args.get("state","").lower()
        valve_control(state)
        return jsonify(ok=True)
    except Exception as e:
        app.logger.exception("Valve error")
        return jsonify(ok=False,error=str(e)),400

@app.route("/stop")
def stop():
    try:
        move_base(0,0)
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False,error=str(e)),502

@app.route("/start_scan")
def start_scan():
    """
    Placeholder for autonomous scanning functionality.
    TODO: Implement actual scan logic here
    """
    global AUTO_MOVE
    try:
        with SCAN_THREAD_LOCK:
            app.logger.info("[SCAN] Starting autonomous scan...")
            if ser is None or not ser.is_open:
                return jsonify(ok=False, error="UGV serial is not connected"), 500
            if AUTO_MOVE is None or not AUTO_MOVE.is_alive():
                stop_event.clear()
                AUTO_MOVE = threading.Thread(target=_run_auto_thread, daemon=True) # Thread to run the autonomous movement logic
                AUTO_MOVE.start()
                app.logger.info("[SCAN] Autonomous thread started")
            else:
                app.logger.info("[SCAN] Autonomous thread already running")
        # TODO: Add scan initialization logic
        return jsonify(ok=True, status="scan_started")
    except Exception as e:
        app.logger.exception("Start scan error")
        return jsonify(ok=False, error=str(e)), 500

@app.route("/stop_scan")
def stop_scan():
    """
    Stop the robot and halt autonomous scanning.
    """
    global AUTO_MOVE
    try:
        app.logger.info("[SCAN] Stopping scan and robot...")
        stop_event.set()  # Signal the autonomous thread to stop
        if AUTO_MOVE is not None and AUTO_MOVE.is_alive():
            AUTO_MOVE.join(timeout=1.0)  # Wait for the autonomous movement thread to finish
        # TODO: Add scan cleanup logic
        return jsonify(ok=True, status="scan_stopped")
    except Exception as e:
        app.logger.exception("Stop scan error")
        return jsonify(ok=False, error=str(e)), 500

@app.route("/ai_status")
def ai_status_endpoint():
    """Return the latest AI inference result and system connectivity."""
    with AI_LOCK:
        running = AUTO_MOVE is not None and AUTO_MOVE.is_alive()
        serial_ok = ser is not None and ser.is_open
        return jsonify(
            label=label,
            conf=round(float(conf), 4),
            running=running,
            robot_connected=serial_ok,
        )

@app.route("/scan_results")
def get_scan_results():
    """Return all accumulated per-cycle scan results."""
    with _scan_result_lock:
        return jsonify(results=list(scan_results))

@app.route("/return_to_base")
def return_to_base():
    """
    Placeholder for return to base functionality.
    TODO: Implement navigation logic to return to starting position
    """
    try:
        app.logger.info("[NAV] Returning to base...")
        move_base(0, 0)  # Stop the robot for now
        # TODO: Add return-to-base navigation logic
        return jsonify(ok=True, status="returning_to_base")
    except Exception as e:
        app.logger.exception("Return to base error")
        return jsonify(ok=False, error=str(e)), 500

if __name__=="__main__":
    try:
<<<<<<< HEAD
        #setup_servo()
        AI_MODEL_THREAD = threading.Thread(target=_ai_display_worker, daemon=True) # Thread to handle AI result display
=======
        setup_servo()
        AI_MODEL_THREAD = threading.Thread(target=display, daemon=True) # Thread to handle AI result display
>>>>>>> 0142534c98f239fffde041e9ce1f052f373576fa
        AI_MODEL_THREAD.start()
        app.run(host="0.0.0.0",port=5000, threaded=True, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        if ser is not None and ser.is_open:
            ser.close()
        if AUTO_MOVE is not None and AUTO_MOVE.is_alive():
            stop_event.set()
            AUTO_MOVE.join(timeout=1.0)
        if AI_MODEL_THREAD is not None and AI_MODEL_THREAD.is_alive():
            AI_DISPLAY_STOP.set()  # Unblock display thread if waiting
            AI_MODEL_THREAD.join(timeout=1.0)
        cleanup()
