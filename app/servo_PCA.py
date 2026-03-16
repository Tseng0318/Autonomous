'''
    Servo control for arm.
    Contains arm control and calculation functions.
    reverse kinematic functions unfinished

'''
import time
import board
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import servo

# Retaining gpiozero just for the valve on the Pi's GPIO
from gpiozero import Device, LED
from gpiozero.pins.lgpio import LGPIOFactory

Device.pin_factory = LGPIOFactory()

# Channels on the PCA9685 (0, 1, 2, 3) instead of Pi GPIO pins
servo_channels = [0, 1, 2, 3]
valve_pin = 3
pwms = []

# Global objects
pca = None
VALVE = None

def setup_servo():
    global pca, VALVE
    
    # Initialize I2C bus and the PCA9685
    i2c = busio.I2C(board.SCL, board.SDA)
    pca = PCA9685(i2c)
    pca.frequency = 50  # 50Hz is the standard frequency for analog servos
    
    # Initialize servos on the PCA9685 channels
    for channel in servo_channels:
        # Note: min_pulse and max_pulse vary by servo brand. 
        # 600-2400 is generally a good range for a full 180 degrees.
        s = servo.Servo(
            pca.channels[channel], 
            actuation_range=180, 
            min_pulse=600, 
            max_pulse=2400
        )
        s.angle = 0
        pwms.append(s)
    
    # Initialize the Valve directly on the Pi's GPIO
    VALVE = LED(valve_pin)
    
    print("Servos initialized on PCA9685.")

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
    
    # Clamp angle to 0-180 to prevent Adafruit library ValueErrors
    clamped_angle = max(0.0, min(180.0, float(angle)))

    s = pwms[servo_num - 1]  # servo_num is 1-indexed
    s.angle = clamped_angle
    time.sleep(1)

def cleanup():
    global VALVE
    # Release servos (sets angle to None, killing the PWM signal to stop jitter/heat)
    for s in pwms:
        s.angle = None 
        
    # Deinitialize the I2C device
    if pca:
        pca.deinit()
        
    # Cleanup valve pin
    if VALVE:
        valve_toggle('off')
        
    print("Servos and PCA9685 cleaned up.")

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