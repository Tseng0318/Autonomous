'''
Reference file for doing manual reverse kinematics
Math might be wrong
'''

import math
from ikpy.chain import Chain
from ikpy.link import OriginLink, URDFLink
import numpy as np

L1, L2 = 5, 2.5  # lengths of arm segments

def servo_calculation(x:float, y:float, z:float):
    '''
    Args:
        x, y, z: coordinates in 3D space
    Returns:
        [theta1, theta2, theta3] in degrees
        angles for servo 1, 2, and 3, not yet considering servo 4 the wrist
 
    '''

    serv1 = math.atan2(y, x)  # base rotation

    serv3 = math.acos((x**2 + z**2 - L1**2 - L2**2) / (2 * L1 * L2))  # elbow angle

    part1 = math.atan(z/2)
    part2 = (L2**2 )*math.sin(serv3)
    part3 = L1 + (L2*math.cos(serv3))
    
    serv2 = part1 - math.atan(part2/part3)

    return [math.degrees(serv1), math.degrees(serv2), math.degrees(serv3)]

def servo_calculation2(x:float, y:float, z:float):
    '''
    Args:
        x, y, z: coordinates in 3D space
    Returns:
        [theta1, theta2, theta3] in degrees
        angles for servo 1, 2, and 3, not yet considering servo 4 the wrist
 
    '''
    serv1 = math.atan2(y, x) 
    L3 = math.sqrt(x**2 +z**2)
    b = math.acos((L1**2 + L2**2 - L3**2)/(2*L1*L2))
    a = math.acos((L3**2 + L1**2 - L2**2)/(2*L3*L1))
    serv3 = math.pi - b
    serv2 = a + math.atan(z/x)
    print(math.degrees(math.atan(z/x)))
    
    return [math.degrees(serv1), math.degrees(serv2), math.degrees(serv3)]

L1, L2 = 5.0, 2.5  # lengths of arm segments
arm_chain = Chain(name="3dof_arm", links=[
    OriginLink(),

    # Joint 1 — Base rotation (yaw)
    URDFLink(
        name="base_rotation",
        origin_translation=[0, 0, 0],
        origin_orientation=[0, 0, 0],
        rotation=[0, 0, 1],   # Z-axis
    ),

    # Joint 2 — Shoulder
    URDFLink(
        name="shoulder",
        origin_translation=[0.0, 0.0, 0.5],  # link 1 length
        origin_orientation=[0, 0, 0],
        rotation=[0, 1, 0],   # Y-axis
    ),

    # Joint 3 — Elbow
    URDFLink(
        name="elbow",
        origin_translation=[0.0, 0.0, 0.25],  # link 2 length
        origin_orientation=[0, 0, 0],
        rotation=[0, 1, 0],   # Y-axis
    ),
])

target_position = [2, 2, 2]
ik_solution = arm_chain.inverse_kinematics(
    target_position
)
degrees =  []
for ik in ik_solution:
    degrees.append(math.degrees(ik))

print(degrees)
print(servo_calculation(2,2,2))
print(servo_calculation2(2,2,2))