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
import os, time, logging, json
import threading
import numpy as np
from collections import deque

# --- Hardware imports (Pi-only; stubbed on Windows/dev) ---
HARDWARE_AVAILABLE = True

try:
    import serial
    from app.servo_final import set_angle, setup_servo, cleanup, valve_toggle
    from base.new_main import main as auto
    from base.station import main as station
except Exception as _hw_err:
    import warnings
    warnings.warn(f"[HW] Pi hardware unavailable: {_hw_err}. Running in display-only mode.")
    HARDWARE_AVAILABLE = False
    serial = None
    def set_angle(*a, **kw): pass
    def setup_servo(): pass
    def cleanup(): pass
    def valve_toggle(*a, **kw): pass
    def auto(*a, **kw): pass



app = Flask(__name__, template_folder="templates")
# Keep UI edits visible immediately in local runs (no stale cached templates/static files).
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
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

try:
    ser = serial.Serial(PORT_UGV, BAUD_UGV, timeout=0.02) if serial else None  # connect to ports
except Exception:
    ser = None


stop_event = threading.Event()
AUTO_MOVE = None
SCAN_THREAD_LOCK = threading.Lock()

STATION_STOP_EVENT = threading.Event()
STATIONS_MOVE = None
STATIONS_THREAD_LOCK = threading.Lock()

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
_station_result_by_name = {name: None for name in _STATION_NAMES}
_pending_station_scans = deque()

# AI decision policy for dashboard output
UNCERTAIN_MIN_CONF = 0.50
UNCERTAIN_HIGH_MIN_CONF = 0.60
CERTAIN_MIN_CONF = 0.75

def _classify_ai_decision(lbl: str, c: float) -> str:
    """Confidence-band classifier used by both real-time status and scan rows.

    Rule set:
    - < 0.50: Clean
    - 0.50 to < 0.75: Uncertain
    - >= 0.75: Rust
    """
    if c < UNCERTAIN_MIN_CONF:
        return "Clean"
    if c < CERTAIN_MIN_CONF:
        return "Uncertain"
    return "Rust"

def _risk_band(c: float) -> str:
    if c >= CERTAIN_MIN_CONF:
        return "High"
    if c >= UNCERTAIN_HIGH_MIN_CONF:
        return "Moderate"
    if c >= UNCERTAIN_MIN_CONF:
        return "Low"
    return "Low"

def _recommendation(decision: str, c: float) -> str:
    """Text shown in AI status recommendation field."""
    if decision == "Rust":
        return "Immediate treatment required"
    if decision == "Uncertain":
        return "Preventive treatment advised" if c >= UNCERTAIN_HIGH_MIN_CONF else "Monitor"
    return "Monitor"

def _station_action(decision: str, c: float) -> str:
    """Action shown in scan results table."""
    if decision == "Rust":
        return "Spray Activated"
    if decision == "Uncertain":
        return "Spray Recommended" if c >= UNCERTAIN_HIGH_MIN_CONF else "Monitor"
    return "Monitor"

def reset_station_state() -> None:
    """Reset station scan state for a new station-to-station mission."""
    global _current_station_idx
    with _scan_result_lock:
        _current_station_idx = 0
        _pending_station_scans.clear()
        for station_name in _STATION_NAMES:
            _station_result_by_name[station_name] = None
        scan_results.clear()

def record_station_ai_scan(station_name: str, lbl: str, c: float, p) -> None:
    """Publish one AI scan result for the specific physical station reached."""
    station_name = str(station_name).strip().upper()
    if station_name not in _STATION_NAMES:
        raise ValueError(f"Unknown station '{station_name}'. Expected one of {_STATION_NAMES}")

    with _scan_result_lock:
        _pending_station_scans.append({
            "station": station_name,
            "label": lbl,
            "conf": float(c),
            "probs": p,
        })
    AI_CHANGED.set()

def _ai_display_worker():
    """Background thread: fires every time detect_rust() produces a new result."""
    global label, conf, probs, _current_station_idx
    while not AI_DISPLAY_STOP.is_set():
        AI_CHANGED.wait()  # Block until approach.py sets the event
        processed_station_payload = False

        while not AI_DISPLAY_STOP.is_set():
            with _scan_result_lock:
                payload = _pending_station_scans.popleft() if _pending_station_scans else None

            if payload is None:
                if processed_station_payload:
                    break
                # Fallback for generic scan flow that does not publish station name.
                with AI_LOCK:
                    lbl = label
                    c = float(conf)
                with _scan_result_lock:
                    station = _STATION_NAMES[_current_station_idx % len(_STATION_NAMES)]
                    _current_station_idx += 1
                break

            station = payload["station"]
            lbl = payload["label"]
            c = float(payload["conf"])
            p = payload.get("probs", [])
            processed_station_payload = True
            # Keep shared latest AI status in sync with published station scans.
            with AI_LOCK:
                label = lbl
                conf = c
                probs = p

            decision = _classify_ai_decision(lbl, c)
            action = _station_action(decision, c)
            entry = {
                "station": station,
                "score": round(c, 4),
                "decision": decision,
                "action": action,
                "time": time.strftime("%H:%M:%S"),
            }
            with _scan_result_lock:
                # Keep one latest result per station for real mission display.
                _station_result_by_name[station] = entry
                scan_results[:] = [
                    _station_result_by_name[s]
                    for s in _STATION_NAMES
                    if _station_result_by_name[s] is not None
                ]
            app.logger.info(f"[DISPLAY] Station {station}: {decision} ({c:.2%})")

        if not processed_station_payload and not AI_DISPLAY_STOP.is_set():
            decision = _classify_ai_decision(lbl, c)
            action = _station_action(decision, c)
            entry = {
                "station": station,
                "score": round(c, 4),
                "decision": decision,
                "action": action,
                "time": time.strftime("%H:%M:%S"),
            }
            with _scan_result_lock:
                _station_result_by_name[station] = entry
                scan_results[:] = [
                    _station_result_by_name[s]
                    for s in _STATION_NAMES
                    if _station_result_by_name[s] is not None
                ]
            app.logger.info(f"[DISPLAY] Station {station}: {decision} ({c:.2%})")

        AI_CHANGED.clear()


def _run_auto_thread():
    try:
        auto(stop_event, ser)
    except Exception as e:
        app.logger.exception(f"[AUTO] Autonomous thread crashed: {e}")

def _run_stations_thread():
    try:
        station(STATION_STOP_EVENT, ser)
    except Exception as e:
        app.logger.exception(f"[AUTO] Autonomous thread crashed: {e}")

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
    if STATIONS_MOVE is not None and STATIONS_MOVE.is_alive():
        print("Stop stations scan before starting this functionality")
        return
    try:
        with SCAN_THREAD_LOCK:
            app.logger.info("[SCAN] Starting autonomous scan...")
            if ser is None or not ser.is_open:
                return jsonify(ok=False, error="UGV serial is not connected"), 500
            reset_station_state()
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
    Stations and normal scan wont be running at the same time
    """
    global AUTO_MOVE, STATIONS_MOVE
    try:
        app.logger.info("[SCAN] Stopping scan and robot...")
        if AUTO_MOVE is not None and AUTO_MOVE.is_alive():
            stop_event.set()  # Signal the autonomous thread to stop
            AUTO_MOVE.join(timeout=1.0)  # Wait for the autonomous movement thread to finish
        elif STATIONS_MOVE is not None and STATIONS_MOVE.is_alive():
            STATION_STOP_EVENT.set()
            AUTO_MOVE.join(timeout=10.0) 
        # TODO: Add scan cleanup logic
        return jsonify(ok=True, status="scan_stopped")
    except Exception as e:
        app.logger.exception("Stop scan error")
        return jsonify(ok=False, error=str(e)), 500

@app.route("/ai_status")
def ai_status_endpoint():
    """Return the latest AI inference result and system connectivity."""
    with AI_LOCK:
        c = round(float(conf), 4)
        running = AUTO_MOVE is not None and AUTO_MOVE.is_alive()
        serial_ok = ser is not None and ser.is_open
        decision = _classify_ai_decision(label, c)
        return jsonify(
            label=label,
            conf=c,
            decision=decision,
            risk_score=c,
            future_risk=_risk_band(c),
            recommendation=_recommendation(decision, c),
            uncertain_min_conf=UNCERTAIN_MIN_CONF,
            uncertain_high_min_conf=UNCERTAIN_HIGH_MIN_CONF,
            certain_min_conf=CERTAIN_MIN_CONF,
            running=running,
            robot_connected=serial_ok,
        )

@app.route("/scan_results")
def get_scan_results():
    """Return one latest result per station in A/B/C order."""
    with _scan_result_lock:
        ordered = [
            _station_result_by_name[s]
            for s in _STATION_NAMES
            if _station_result_by_name[s] is not None
        ]
        return jsonify(results=ordered)

@app.route("/return_to_base")
def return_to_base():
    """
    Placeholder for autonomous scanning functionality.
    TODO: Implement actual scan logic here
    """
    global STATIONS_MOVE
    if AUTO_MOVE is not None and AUTO_MOVE.is_alive:
        print("stop scanning before starting this functionality")
        return
    try:
        with STATIONS_THREAD_LOCK:
            app.logger.info("[SCAN] Starting autonomous scan...")
            if ser is None or not ser.is_open:
                return jsonify(ok=False, error="UGV serial is not connected"), 500
            reset_station_state()
            if STATIONS_MOVE is None or not STATIONS_MOVE.is_alive():
                stop_event.clear()
                STATIONS_MOVE = threading.Thread(target=_run_stations_thread, daemon=True) # Thread to run the autonomous movement logic
                STATIONS_MOVE.start()
                app.logger.info("[SCAN] Autonomous thread started")
            else:
                app.logger.info("[SCAN] Autonomous thread already running")
        # TODO: Add scan initialization logic
        return jsonify(ok=True, status="scan_started")
    except Exception as e:
        app.logger.exception("Start scan error")
        return jsonify(ok=False, error=str(e)), 500

if __name__=="__main__":
    try:
        setup_servo()
        AI_MODEL_THREAD = threading.Thread(target=_ai_display_worker, daemon=True) # Thread to handle AI result display
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
        if STATIONS_MOVE is not None and STATIONS_MOVE.is_alive():
            STATION_STOP_EVENT.set()
            AUTO_MOVE.join(timeout=10.0) 
        cleanup()
