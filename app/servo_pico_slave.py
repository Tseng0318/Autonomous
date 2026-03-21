'''
    Servo control for arm.
    Contains arm control and calculation functions.
    reverse kinematic functions unfinished

'''
from machine import Pin, PWM
import time
import sys

servo_pins = [0,1,2,3]
valve_pin = 3
pwms = []

def setup_servo():
    for s in servo_pins:
        servo = PWM(Pin(s))
        servo.freq(50)
        pwms.append(servo)

    for pin in pwms:
        set_angle(pin,0)
    
    print("Servos initialized.")

def set_angle(servo_num: int, angle: float):
    """
    Set the angle of a specified servo.
    Args:
        servo_num: the servo number (1-4)
        angle: desired angle (0 to 180)
    """
    min_duty = 1638   # ~0.5 ms
    max_duty = 8192   # ~2.5 ms

    duty = int(min_duty + (angle / 180) * (max_duty - min_duty))
    pwms[servo_num - 1].duty_u16(duty)


def cleanup():
    print("Cleaning up...")
    for pwm in pwms:
        try:
            pwm.deinit()   # stops PWM signal
        except:
            pass

    pwms.clear()

    print("Cleanup complete.")
    
def main():
    while True:
        line = sys.stdin.readline().strip()
        if not line:
            continue
        try:
            print("Received")
            if line == 'set':
                setup_servo()

            elif line == 'clean':
                cleanup()

            else:
                parts = line.split(',')

                if len(parts) == 2:
                    servo_num = int(parts[0])
                    angle = float(parts[1])
                    set_angle(servo_num, angle)

        except Exception as e:
            print("Error:", e)