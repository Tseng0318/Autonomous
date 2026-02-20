# file: base_detec.py
#
# this is the module we use to scan for the pattern
# the pattern would be paste on our station

import cv2
import cv2.aruco as aruco
import numpy as np
import subprocess
import os

# CONFIG, important, do not change if not necessary
MARKER_SIZE = 10.0   # Physical width of our image in cm
FOCAL_LENGTH = 470   # Calibration for Camera Module 3, this is the focal length of our camera module
BASE_ID = 0          # The ID number of the marker on your base
WIDTH, HEIGHT = 640, 480

# Fix for the "Wayland/Qt" graphics error on Pi 5
os.environ["QT_QPA_PLATFORM"] = "xcb"

# CAMERA PIPE 
# do not change anything here
#  rpicam-vid to get the stream and pipe it into Python
command = [
    'rpicam-vid', '-t', '0', 
    '--width', str(WIDTH), 
    '--height', str(HEIGHT),
    '--inline', '--nopreview', 
    '--codec', 'mjpeg', 
    '--autofocus-mode', 'continuous', 
    '-o', '-'
]

process = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=10**8)

# ARUCO SETUP
# Using the 4x4 dictionary for better distance detection
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
parameters = aruco.DetectorParameters()
detector = aruco.ArucoDetector(aruco_dict, parameters)

print(f"ROVER VISION ACTIVE")
print(f"Targeting Base ID: {BASE_ID}")
print("Press 'q' to exit.")

buffer = b""

try:
    while True:
        # Read data from the camera pipe
        chunk = process.stdout.read(4096)
        if not chunk: break
        buffer += chunk
        
        # Identify JPEG frame boundaries
        a = buffer.find(b'\xff\xd8') # Start of JPEG
        b = buffer.find(b'\xff\xd9') # End of JPEG
        
        if a != -1 and b != -1:
            jpg = buffer[a:b+2]
            buffer = buffer[b+2:]
            
            # Decode JPEG into OpenCV image
            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            
            if frame is not None:
                # DETECTION LOGIC
                corners, ids, rejected = detector.detectMarkers(frame)
                
                if ids is not None and BASE_ID in ids:
                    # Find index of our specific Base ID
                    idx = np.where(ids.flatten() == BASE_ID)[0][0]
                    c = corners[idx][0] # 4 corners of the marker
                    
                    # Distance calculation
                    # pixel_width = distance between top-left and top-right corners
                    pixel_width = np.linalg.norm(c[0] - c[1])
                    distance = (MARKER_SIZE * FOCAL_LENGTH) / max(pixel_width, 1)
                    
                    # Angle calculation
                    # marker_center_x compared to image center (320)
                    marker_center_x = (c[0][0] + c[2][0]) / 2
                    error_x = marker_center_x - (WIDTH / 2)
                    
                    # Define Steering Action
                    if error_x < -60:
                        action = "LEFT"
                    elif error_x > 60:
                        action = "RIGHT"
                    else:
                        action = "STRAIGHT"

                    # STOP LOGIC (Docking)
                    if distance < 15.0:
                        action = "STOP / DOCKED"

                    # Print to terminal
                    print(f"Dist: {distance:.1f}cm | Steering: {action}      ", end="\r")
                    
                    # Draw on Video Window (just to show the result, not necessary)
                    aruco.drawDetectedMarkers(frame, corners, ids)
                    cv2.putText(frame, f"{distance:.1f}cm", (int(c[0][0]), int(c[0][1]-10)), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(frame, action, (20, 440), 
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
                else:
                    print("Searching for Base...                ", end="\r")

                # SHOW WINDOW
                cv2.imshow("Rover View", frame)
                
                # Check for exit command q
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                if cv2.getWindowProperty("Rover View", cv2.WND_PROP_VISIBLE) < 1:
                    break

except KeyboardInterrupt:
    print("\nInterrupted by user.")

finally:
    # Cleanup
    print("\nClosing Camera and Windows...")
    process.terminate()
    cv2.destroyAllWindows()
