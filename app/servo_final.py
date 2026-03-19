'''
    Servo control for arm.
    Contains arm control and calculation functions.
    reverse kinematic functions unfinished

'''

from gpiozero import Device
from gpiozero.pins.lgpio import LGPIOFactory

Device.pin_factory = LGPIOFactory()
from gpiozero import AngularServo, LED
from time import sleep
import time
import math

servo_pins = [26, 16, 13, 6]
valve_pin = 3
pwms = []

def setup_servo():
    for pin in servo_pins:
        pwms.append(AngularServo(pin, min_angle=0, max_angle=180, initial_angle=0))
    
    global VALVE
    VALVE = LED(valve_pin)
    
    print("Servos initialized.")

def set_angle(servo_num: int, angle: float):
    """
    Set the angle of a specified servo.
    Args:
        servo_num: the servo number (1-4)
        angle: desired angle (0 to 180)
    """
    if servo_num < 1 or servo_num > len(pwms):
        print("Invalid servo number")
        return 
    

    servo = pwms[servo_num - 1]  # servo_num is 1-indexed
    servo.angle = angle
    sleep(1)

def cleanup():
    global VALVE
    for servo in pwms:
        servo.close()
    
    VALVE.off()
    print("Servos cleaned up.")

def generic_spray():
    set_angle(4,0)
    #TODO: Open valve function
    valve_toggle('on')
    set_angle(4,45)
    sleep(2)
    set_angle(4,90)
    sleep(2)
    set_angle(4,135)
    sleep(2)
    set_angle(4,90)
    sleep(2)
    set_angle(4,45)
    sleep(2)
    valve_toggle('off')
    
    #TODO: Close valve function
    set_angle(4,0)

def valve_toggle(state):
    if state.lower == 'on':
        VALVE.on()
    else:
        VALVE.off()
if __name__ == "__main__":
    try:
       setup_servo()
       while True:
            ser = input("Enter servo number:")
            angle = float(input("Enter angle (0-180):"))
            set_angle(int(ser), angle)
            print(f"servo {ser} moved to {angle} degrees.")
            time.sleep(2)
       
    except KeyboardInterrupt:
        cleanup()