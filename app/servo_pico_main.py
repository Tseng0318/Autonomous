'''
    Servo control for arm.
    Contains arm control and calculation functions.
    reverse kinematic functions unfinished

'''
import serial
from gpiozero import Device
from gpiozero.pins.lgpio import LGPIOFactory

Device.pin_factory = LGPIOFactory()
from gpiozero import AngularServo, LED
from time import sleep
import time
import math

valve_pin = 3

def setup_servo():
    global ser
    ser = serial.Serial('/dev/serial/by-id/usb-MicroPython_Board_in_FS_mode_e66368254f51b032-if00', 9600, timeout=1)

    command = f"set\n"
    ser.write(command.encode('utf-8'))
    
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

    command = f"{servo_num},{angle}\n"
    ser.write(command.encode('utf-8'))

    sleep(1)

def cleanup():
    global VALVE
    command = f"clean\n"
    ser.write(command.encode('utf-8'))
    
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
            ser_num = input("Enter servo number:")
            angle = float(input("Enter angle (0-180):"))
            set_angle(int(ser_num), angle)
            print(f"servo {ser_num} moved to {angle} degrees.")
            time.sleep(2)
       
    except KeyboardInterrupt:
        cleanup()
