'''
Reference file for reverse kinemtics using ikpy
'''

import math
from ikpy.chain import Chain
from ikpy.link import OriginLink, URDFLink
import numpy as np

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





target_position = [1, 1, 1]
ik_solution = arm_chain.inverse_kinematics(
    target_position
)
print(f"IK Solution: {ik_solution}")

for ik in ik_solution:
    print(f"{math.degrees(ik):.2f} degrees")