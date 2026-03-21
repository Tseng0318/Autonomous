import serial
import time

# Initialize connection using your specific path
ser = serial.Serial('/dev/serial/by-id/usb-MicroPython_Board_in_FS_mode_e66368254f51b032-if00', 9600, timeout=1)
time.sleep(2) # Give the connection a moment to settle

try:
    # 1. Send a message
    message = "Ping\n"
    ser.write(message.encode('utf-8'))
    print(f"Sent: {message.strip()}")

    # 2. Wait for and read the reply
    reply = ser.readline().decode('utf-8').strip()
    
    if reply:
        print(f"Received from Pico: {reply}")
    else:
        print("No response received.")

finally:
    ser.close()