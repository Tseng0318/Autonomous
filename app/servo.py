from rpi_hardware_pwm import HardwarePWM
import time

# Initialize PWM channel 0 at 50Hz (standard for servos)
# On Pi 5, PWM0 is typically accessible on GPIO 12 or 18
servo = HardwarePWM(pwm_channel=0, hz=50)
servo.start(0)

def set_angle(angle):
    """
    Converts an angle (0-180) to a duty cycle (approx 2.5% to 12.5%).
    Calculation: (Angle / 18) + 2.5
    """
    duty_cycle = (angle / 18.0) + 2.5
    servo.change_duty_cycle(duty_cycle)

try:
    print("Starting servo sweep. Press Ctrl+C to stop.")
    while True:
        # Sweep from 0 to 180 degrees
        for angle in range(0, 181, 10):
            print("Test")
            set_angle(angle)
            time.sleep(0.1)
        
        # Sweep back from 180 to 0 degrees
        for angle in range(180, -1, -10):
            set_angle(angle)
            time.sleep(0.1)

except KeyboardInterrupt:
    print("\nShutting down...")
finally:
    servo.stop()
