'''
    Servo control for arm.
    Contains arm control and calculation functions.
    reverse kinematic functions unfinished

    pip3 install adafruit-circuitpython-servokit

'''

from gpiozero import Device
from gpiozero.pins.lgpio import LGPIOFactory

Device.pin_factory = LGPIOFactory()
from gpiozero import AngularServo, LED
from time import sleep
import time
import math
import time
from adafruit_servokit import ServoKit

servo_pins = [0, 1, 2, 3]
valve_pin = 3

kit = ServoKit(channels=16)

kit.frequency = 50 

def setup_servo():
    for pin in servo_pins:
        kit.servo[pin].angle = 0
    
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
    if servo_num < 1 or servo_num > 4:
        print("Invalid servo number")
        return 
    if angle<0 or angle>180:
        print("angle outside limits")
        return
    
    kit.servo[servo_num - 1].angle = angle 
    sleep(1)

def cleanup():
    global VALVE
    # Cleanup valve pin
    if VALVE:
        valve_toggle('off')
    print("Servos cleaned up.")

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