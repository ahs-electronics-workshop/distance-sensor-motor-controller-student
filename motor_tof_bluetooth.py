import time
import board
import pwmio
import io
from adafruit_motor import motor

import ew_distance as ew_dist
ew_dist.setup()

import ew_uart as ua
ua.setup("morris-ble2")

PWM_PIN_A1 = board.D10  # pick any pwm pins on their own channels
PWM_PIN_A2 = board.D9
PWM_PIN_B1 = board.D7  # pick any pwm pins on their own channels
PWM_PIN_B2 = board.D8

# DC motor setup
pwm_a1 = pwmio.PWMOut(PWM_PIN_A1, frequency=50)
pwm_a2 = pwmio.PWMOut(PWM_PIN_A2, frequency=50)
motor1 = motor.DCMotor(pwm_a1, pwm_a2)

pwm_b1 = pwmio.PWMOut(PWM_PIN_B1, frequency=50)
pwm_b2 = pwmio.PWMOut(PWM_PIN_B2, frequency=50)
motor2 = motor.DCMotor(pwm_b1, pwm_b2)


motor1.throttle = 0
motor2.throttle = 0

print("-- throttle 1:", motor1.throttle)
print("-- throttle 2:", motor2.throttle)

max_rpm = 145  # Motor's max RPM at 100% duty cycle
stop_time = None
reverse_motors = False

# Function to get estimated RPM
def get_estimated_rpm(duty_cycle):
    return (duty_cycle / 65535) * max_rpm

def get_all_rpm():
    return [
        get_estimated_rpm(pwm_a1.duty_cycle),
        get_estimated_rpm(pwm_a2.duty_cycle),
        get_estimated_rpm(pwm_b1.duty_cycle),
        get_estimated_rpm(pwm_b2.duty_cycle)
    ]

def write_rpms(rpms):
    msg = f"a1: {rpms[0]:.2f}; "
    msg += f"a2: {rpms[1]:.2f}\n"
    msg += f"b1: {rpms[2]:.2f}; "
    msg += f"b2: {rpms[3]:.2f}"
    ua.write(msg)

def check_reverse():
    if stop_time is not None:
        return time.monotonic() - stop_time >= 5
    return False

def check_stop():
    global stop_time
    if stop_time is None and motor1.throttle == 0 and motor2.throttle == 0:
        stop_time = time.monotonic()  # Record the time when stopped
    elif motor1.throttle > 0 or motor2.throttle > 0:
        stop_time = None

def set_throttle(m1_throt, m2_throt):
    if -1 <= m1_throt <= 1 and  -1 <= m2_throt <= 1:
        motor1.throttle = -1 * m1_throt 
        motor2.throttle = m2_throt
    check_stop()

def maneuver_away_from_barrier():
    while ew_dist.read_distance() < 40:
        set_throttle(-1, -1)
    elapsed = time.monotonic()
    while time.monotonic() - elapsed < 4:
        set_throttle(1, 0)
    
counter = 0
while True:
    ua.connect()
    while ua.connected():
        counter += 1

        if counter % 50000 == 0:
            write_rpms(get_all_rpm())
                
        if ua.in_waiting():
            data = ua.read(ua.in_waiting())
            if data:
                text = data.decode("utf-8").strip()
                print("Text Sent: ", text)
                if text and text == "w":
                    set_throttle(1, 1)
                elif text and text == "s":
                    set_throttle(0.1, 0.1)                
                elif text and text == "a":
                    set_throttle(1, 0.0)
                elif text and text == "d":
                    set_throttle(0, 1)
                write_rpms(get_all_rpm())
        dist = ew_dist.read_distance()
        if dist:
            print(f"Distance: {dist} cm")            
            if dist > 70:
                set_throttle(1.0, 1.0)
            elif dist > 60:
                set_throttle(0.9, 0.9)
            elif dist > 50:
                set_throttle(0.8, 0.8)
            elif dist > 40:
                set_throttle(0.7, 0.7)
            elif dist > 30:
                set_throttle(0.5, 0.6)
            elif dist > 20:
                set_throttle(0.4, 0.4)
            else:
                set_throttle(0, 0)
                if check_reverse():
                    maneuver_away_from_barrier()
        