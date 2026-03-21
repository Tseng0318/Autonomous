'''
    Servo control for arm.
    Contains arm control and calculation functions.
    reverse kinematic functions unfinished

'''
from machine import Pin, PWM, UART
import time

uart = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))

servo_pins = [26, 16, 13, 6]
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
    try:
        while True:
            if uart.any():
                data = uart.readline().decode('utf-8').strip().strip('\n')
                if data == 'set':
                    setup_servo()
                elif data == 'clean':
                    cleanup()
                else:
                    data = data.split(',')
                    angle = float(data[1])
                    servo_num = int(data[0])
                    set_angle(servo_num, angle)
    except KeyboardInterrupt:
        cleanup()