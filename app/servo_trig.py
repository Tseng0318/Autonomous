import math

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

    part1 = math.atan2(z/2)
    part2 = (L2**2 )*math.sin(serv3)
    part3 = L1 + (L2*math.cos(serv3))
    
    serv2 = part1 - math.atan(part2/part3)

    return [serv1, serv2, serv3]

