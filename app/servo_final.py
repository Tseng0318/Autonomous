'''
    Servo control for arm.
    Contains control and calculation functions.

'''


from gpiozero import AngularServo
from time import sleep
import time
import math
'''
from ikpy.chain import Chain
from ikpy.link import OriginLink, URDFLink
import numpy as np
'''
servo_pins = [12, 11, 13, 15]
pwms = []
'''
L1, L2 = 5.0, 2.5  # lengths of arm segments
arm_chain = Chain(name="3dof_arm", links=[
    OriginLink(),

    # Joint 1 — Base rotation (yaw)
    URDFLink(
        name="base_rotation",
        translation_vector=[0, 0, 0],
        orientation=[0, 0, 0],
        rotation=[0, 0, 1],   # Z-axis
    ),

    # Joint 2 — Shoulder
    URDFLink(
        name="shoulder",
        translation_vector=[0.0, 0.0, 0.5],  # link 1 length
        orientation=[0, 0, 0],
        rotation=[0, 1, 0],   # Y-axis
    ),

    # Joint 3 — Elbow
    URDFLink(
        name="elbow",
        translation_vector=[0.0, 0.0, 0.25],  # link 2 length
        orientation=[0, 0, 0],
        rotation=[0, 1, 0],   # Y-axis
    ),
])
'''



def setup_servo():
    for pin in servo_pins:
        pwms.append(AngularServo(pin, min_angle=0, max_angle=180, initial_angle=0))
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
    for servo in pwms:
        servo.close()
    print("Servos cleaned up.")

'''
def servo_calculation(x:float, y:float, z:float):
    '''
'''
    Args:
        x, y, z: coordinates in 3D space
    Returns:
        [theta1, theta2, theta3] in degrees
        angles for servo 1, 2, and 3, not yet considering servo 4 the wrist
    '''
'''
    target_position = [x, y, z]
    ik_solution = arm_chain.inverse_kinematics(
        target_position
    )
    degrees =  []
    for ik in ik_solution:
        degrees.append(math.degrees(ik))
    return degrees  
'''

def move_arm(x:float, y:float, z:float):
    '''
    Move the robotic arm to the specified (x, y, z) coordinates.
    '''
    angles = servo_calculation(x, y, z)
    for i in range(3):
        set_angle(i + 1, angles[i])

    return 1

def generic_spray():
    set_angle(4,0)
    #TODO: Open valve function

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
    
    #TODO: Close valve function
    set_angle(4,0)


if __name__ == "__main__":
    try:
       while True:
            ser = input("Enter servo number:")
            angle = float(input("Enter angle (0-180):"))
            setup_servo()
            set_angle(int(ser), angle)
            cleanup()
            #app.logger.info(f"servo {ser} moved to {angle} degrees.")
            print(f"servo {ser} moved to {angle} degrees.")
            exit(0)
            time.sleep(2)
       
    except Exception as e:
        #app.logger.exception("Error in servo control")
        print(f"Error in servo control: {e}")
    finally:
        cleanup()