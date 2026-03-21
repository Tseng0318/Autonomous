import serial
import time
from gpiozero import LED

# Configuration
SERIAL_PORT = '/dev/serial/by-id/usb-MicroPython_Board_in_FS_mode_e66368254f51b032-if00'
VALVE_PIN = 3

ser = None
VALVE = None

def setup_servo():
    global ser, VALVE
    # Initialize Serial
    ser = serial.Serial(SERIAL_PORT, 9600, timeout=1)
    time.sleep(2) # IMPORTANT: Wait for Pico to reboot/settle
    
    # Initialize Valve
    VALVE = LED(VALVE_PIN)
    
    # Tell Pico to setup
    ser.write(b"set\n")
    response = ser.readline().decode().strip()
    print(f"Pico says: {response}")

def set_angle(servo_num: int, angle: float):
    if ser and ser.is_open:
        command = f"{servo_num},{angle}\n"
        ser.write(command.encode('utf-8'))
        
        # Read the confirmation from Pico
        response = ser.readline().decode('utf-8').strip()
        if response:
            print(f"Pico confirmed: {response}")

def valve_toggle(state):
    if state.lower() == 'on': # Added () here
        VALVE.on()
        print("Valve OPEN")
    else:
        VALVE.off()
        print("Valve CLOSED")

def cleanup():
    if ser and ser.is_open:
        ser.write(b"clean\n")
        time.sleep(0.1)
        ser.close()
    if VALVE:
        VALVE.off()
    print("Cleanup complete.")

if __name__ == "__main__":
    try:
        setup_servo()
        while True:
            val = input("Enter 's' for spray or 'm' for manual move (or 'q' to quit): ").lower()
            
            if val == 'q':
                break
            elif val == 'm':
                s_num = input("Enter servo (1-4): ")
                ang = input("Enter angle (0-180): ")
                set_angle(int(s_num), float(ang))
            elif val == 's':
                # Example spray sequence
                valve_toggle('on')
                set_angle(4, 45)
                time.sleep(1)
                set_angle(4, 135)
                time.sleep(1)
                valve_toggle('off')

    except KeyboardInterrupt:
        pass
    finally:
        cleanup()