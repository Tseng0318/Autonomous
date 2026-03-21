from machine import Pin, PWM
import time
import sys
import select

servo_pins = [0, 1, 2, 3]
pwms = []

def setup_servo():
    # Clear existing if re-initializing
    cleanup()
    for s in servo_pins:
        servo = PWM(Pin(s))
        servo.freq(50)
        pwms.append(servo)
    
    # Set all to 0 degrees initially
    for i in range(len(pwms)):
        set_angle(i + 1, 0)
    
    print("Servos initialized.")

def set_angle(servo_num: int, angle: float):
    if not pwms:
        return
    min_duty = 1638   # ~0.5 ms
    max_duty = 8192   # ~2.5 ms
    duty = int(min_duty + (angle / 180) * (max_duty - min_duty))
    # Correct index: user sends 1-4, list is 0-3
    pwms[servo_num - 1].duty_u16(duty)

def cleanup():
    for pwm in pwms:
        try:
            pwm.deinit()
        except:
            pass
    pwms.clear()
    print("Cleanup complete.")

# Main Loop
line = ""
while True:
    # Check if data is available on USB Serial
    if select.select([sys.stdin], [], [], 0.1)[0]:
        line = sys.stdin.readline().strip()
        
        if not line:
            continue

        try:
            if line == 'set':
                setup_servo()
            elif line == 'clean':
                cleanup()
            else:
                parts = line.split(',')
                if len(parts) == 2:
                    s_num = int(parts[0])
                    ang = float(parts[1])
                    set_angle(s_num, ang)
                    print(f"Moved {s_num} to {ang}") # This is the reply the Pi sees
        except Exception as e:
            print("Error:", e)