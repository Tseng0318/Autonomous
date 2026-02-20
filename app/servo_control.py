import RPi.GPIO as GPIO
import time
import math
import app.logger

# BCM pin numbers for 4 servos
servo_pins = [12, 11, 13, 15]
pwms = []  # list to store PWM objects for each servo
L1, L2 = 10.0, 10.0  # lengths of arm segments

def setup_servo():
    GPIO.setmode(GPIO.BCM)
    for pin in servo_pins:
        GPIO.setup(pin, GPIO.OUT)
        pwm = GPIO.PWM(pin, 50)  # 50Hz frequency for servos
        pwm.start(0)
        pwms.append(pwm)
    print("Servos initialized.")

def set_angle(servo_num, angle):
    """
    Set the angle of a specified servo.
    Args:
        servo_num: the servo number (1-4)
        angle: desired angle (0-180)
    """
    if servo_num < 1 or servo_num > len(pwms):
        app.logger.error("Invalid servo number")
        return

    duty = angle / 18 + 2  # Convert angle to duty cycle
    pwm = pwms[servo_num - 1]  # servo_num is 1-indexed
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0)  # stop sending signal

def cleanup():
    for pwm in pwms:
        pwm.stop()
    GPIO.cleanup()
    print("GPIO cleaned up.")

def servo_calculation(x, y, z):
    '''
    Args:
        x, y, z: coordinates in 3D space
    Returns:
        [theta1, theta2, theta3] in degrees
        angles for servo 1, 2, and 3 not yet considering servo 4 the wrist


    Generated placeholder for inverse kinematics calculation
    Need to look into the math 
    '''

    # Base rotation (azimuth)
    # If x and y are both zero, set base to 0 by convention
    if x == 0 and y == 0:
        theta1 = 0.0
    else:
        theta1 = math.degrees(math.atan2(y, x))

    # Planar distance from base axis to target
    r = math.hypot(x, y)
    # Distance from shoulder joint to target point
    d = math.hypot(r, z)

    # Check reachability
    if d > (L1 + L2) + 1e-9 or d < abs(L1 - L2) - 1e-9:
        raise ValueError(f"Target out of reach (d={d:.2f}, L1+L2={L1+L2})")

    # Law of cosines for elbow angle (q2)
    # cos_q2 = (d^2 - L1^2 - L2^2) / (2*L1*L2)
    cos_q2 = (d * d - L1 * L1 - L2 * L2) / (2 * L1 * L2)
    cos_q2 = max(-1.0, min(1.0, cos_q2))
    # Choose elbow-down solution by default (negative sin)
    sin_q2 = -math.sqrt(max(0.0, 1.0 - cos_q2 * cos_q2))
    q2 = math.atan2(sin_q2, cos_q2)

    # Shoulder angle: angle from horizontal to first link
    # using geometry: q1 = atan2(z, r) - atan2(L2*sin(q2), L1 + L2*cos(q2))
    k1 = L1 + L2 * cos_q2
    k2 = L2 * sin_q2
    q1 = math.atan2(z, r) - math.atan2(k2, k1)

    theta2 = math.degrees(q1)
    theta3 = math.degrees(q2)

    return [theta1, theta2, theta3]