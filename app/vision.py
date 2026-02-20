# File for distance approximation
# Currently only has generated example code
# Must look into actual implementaion and research

import cv2
import numpy as np

# Camera parameters as np array 
# focal lengths and principal point
# filler points added
K = np.array([
    [700, 0, 640],   # fx, 0, cx
    [0, 700, 360],   # 0, fy, cy
    [0, 0, 1]
])

#Distance of LIDAR from camera np
# Needed to compensate for offset between LIDAR and camera
t = np.array([[0], [0], [0]])

#Must translate 

def rust_detected(lidar_points, camera_points, bbox):
    '''
    When rust is detected, function called
    Runs image distance calculations

    Args:
        lidar_points: Nx3 array of points in LIDAR frame where rust is detected
        camera_points: Nx3 array of points in camera frame where rust is detected
        bbox: bounding box of detected rust in image (x1, y1, x2, y2)
    Returns:
        distance to rust in meters (float) or None if no points found
    '''

    projected = project_lidar_to_image(lidar_points, camera_points)
    distance = calculate_distance_to_rust(bbox, projected)
    return distance
    


# Have to figure out how to get points from camera

def project_lidar_to_image(lidar_points, camera_points):
    '''
    Generated Example code

    Args:
        lidar_points: Nx3 array of LIDAR points in LIDAR frame
        camera_points: Nx3 array of corresponding points in camera frame
    Returns:
        Nx3 array of projected points in image frame (u, v, depth)
    '''
    # Convert to homogeneous coordinates (add column of 1s)
    n = lidar_points.shape[0]
    points_hom = np.hstack((lidar_points, np.ones((n, 1))))
    
    # Transform to camera coordinate system
    # P = K * [R|t]
    projection_matrix = K @ t
    points_2d_hom = points_hom @ projection_matrix.T
    
    # Normalize to get (u, v) pixels
    u = points_2d_hom[:, 0] / points_2d_hom[:, 2]
    v = points_2d_hom[:, 1] / points_2d_hom[:, 2]
    depth = points_2d_hom[:, 2] # Distance from camera
    
    return np.column_stack((u, v, depth))

def calculate_distance_to_rust(bbox, projected_points):
    '''
    Calculating distance to rust 

    Args:
        bbox: bounding box of rust in image (x1, y1, x2, y2)
        projected_points: Nx3 array of projected LIDAR points in image frame
    Returns:
        distance to rust in meters (float) or None if no points found
    '''
    x1, y1, x2, y2 = bbox
    
    # Filter points that fall inside the bounding box
    mask = (projected_points[:, 0] >= x1) & (projected_points[:, 0] <= x2) & \
            (projected_points[:, 1] >= y1) & (projected_points[:, 1] <= y2) & \
            (projected_points[:, 2] > 0) # Only points in front of camera
    
    points_in_box = projected_points[mask]
    
    if len(points_in_box) == 0:
        return None
    
    # Use Median to ignore outliers (e.g., points hitting the ground behind the car)
    return np.median(points_in_box[:, 2])