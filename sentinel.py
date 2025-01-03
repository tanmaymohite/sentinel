import face_recognition
import cv2
from gpiozero import AngularServo
from time import sleep, time, strftime, localtime
from pushbullet import Pushbullet
import tkinter as tk
from tkinter import Button, Entry

# Load saved encodings and names
known_faces = []
known_names = []

with open("encodings.txt", "r") as file:
    lines = file.readlines()
    for line in lines:
        data = line.strip().split()
        name = data[0]
        encoding = list(map(float, data[1:]))
        known_names.append(name)
        known_faces.append(encoding)

# OpenCV setup
video_capture = cv2.VideoCapture(0)  # Use 0 for the default camera

# Servo setup
servo = AngularServo(18, min_pulse_width=0.0006, max_pulse_width=0.0023)

# Pushbullet setup
pb = Pushbullet("o.VRM4crr0nOGXk1YTu7f8gFkbkoilcceI")  # Replace with your Pushbullet API key

# Time when the motor was last rotated
last_rotation_time = 0

# Cooldown period in seconds
cooldown_period = 10  # Adjust this value as needed

# Flag to track if a notification has been sent for unknown faces
notification_sent_unknown = False

# Variable to store the generated PIN
generated_pin = ""

# Flag to track motor rotation
motor_rotated = False

# Function to send Pushbullet notification with PIN
def send_pin_notification(pin):
    pb.push_note("Unknown Face Detected", f"Enter PIN: {pin} to access.")

# Function to generate a random 6-digit PIN
def generate_random_pin():
    import random
    return str(random.randint(100000, 999999))

# Function to create GUI for entering PIN
def create_gui():
    root = tk.Tk()
    root.title("Unknown Face Detected")

    label = tk.Label(root, text="Enter PIN:", font=("Helvetica", 16))
    label.grid(row=0, column=0, columnspan=3, pady=10)

    pin_var = tk.StringVar()
    pin_entry = tk.Entry(root, textvariable=pin_var, show="*", font=("Helvetica", 14), state='readonly')
    pin_entry.grid(row=1, column=0, columnspan=3, pady=10)

    # Function to update the PIN entry
    def update_pin(entry):
        pin_var.set(entry)

    # Numeric keypad buttons
    buttons = [
        '7', '8', '9',
        '4', '5', '6',
        '1', '2', '3',
        '0', 'C', 'Submit'
    ]

    # Function to handle button clicks
    def button_click(value):
        if value == 'C':
            update_pin('')
        elif value == 'Submit':
            verify_pin(pin_var.get(), root)
        else:
            update_pin(pin_var.get() + str(value))

    # Create numeric keypad buttons
    row_val, col_val = 2, 0
    for button in buttons:
        tk.Button(root, text=button, font=("Helvetica", 14), width=5, height=2,
                  command=lambda btn=button: button_click(btn)).grid(row=row_val, column=col_val, padx=5, pady=5)
        col_val += 1
        if col_val > 2:
            col_val = 0
            row_val += 1

    root.mainloop()

# Function to verify entered PIN and rotate motor if correct
def verify_pin(entered_pin, root):
    global motor_rotated, notification_sent_unknown
    if entered_pin == generated_pin:
        rotate_motor()
        root.destroy()  # Close the GUI window
        notification_sent_unknown = False  # Reset the notification flag for unknown faces

# Function to rotate the motor
def rotate_motor():
    global last_rotation_time, motor_rotated
    print("Face recognized! Rotating the servo by 90 degrees.")
    servo.angle = 90
    sleep(2)
    servo.angle = 0
    last_rotation_time = time()
    motor_rotated = True
    print("Motor rotated!")

while True:
    ret, frame = video_capture.read()

    # Find all face locations in the current frame
    face_locations = face_recognition.face_locations(frame)
    face_encodings = face_recognition.face_encodings(frame, face_locations)

    # Reset the flag for each new frame
    motor_rotated = False

    # Declare name outside the loop
    name = "Unknown"

    # Compare each face found with known faces
    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        matches = face_recognition.compare_faces(known_faces, face_encoding, tolerance=0.5)

        color = (255, 255, 255)  # Default color (white) for unknown faces

        if True in matches and not motor_rotated:
            # Known face logic
            first_match_index = matches.index(True)
            name = known_names[first_match_index]
            color = (255, 0, 0)  # Blue color for known faces

            # Check if enough time has passed since the last rotation
            if (time() - last_rotation_time) > cooldown_period:
                # Rotate the servo when a known face is recognized
                print(f"Known face recognized ({name})! Rotating the servo by 90 degrees.")
                servo.angle = 90
                sleep(2)
                servo.angle = 0  # You can adjust this angle as needed

                # Update the time of the last rotation
                last_rotation_time = time()

                # Set the flag to indicate that the motor has been rotated
                motor_rotated = True

                # Reset the notification flag for unknown faces
                notification_sent_unknown = False

                # Send a notification for known faces
                current_time = strftime("%Y-%m-%d %H:%M:%S", localtime())
                pb.push_note("Known Face Detected", f"{name} entered your office at {current_time}")
                print("Notification sent for known face!")

        # Display the name and face status in color
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.5, color, 1)

    # Check if it's time to send a notification for unknown faces
    if not motor_rotated and (time() - last_rotation_time) > cooldown_period and not notification_sent_unknown:
        if face_locations:  # Check if there are any faces detected
            # Get the current time
            current_time = strftime("%Y-%m-%d %H:%M:%S", localtime())

            # Generate a random 6-digit PIN for unknown faces
            generated_pin = generate_random_pin()

            # Send a notification with a timestamp and PIN for unknown faces
            send_pin_notification(generated_pin)

            # Create a GUI for PIN entry
            create_gui()  # This will block until the PIN is entered in the GUI

            # Set the flag to True to indicate that the notification has been sent for unknown faces
            notification_sent_unknown = True

            # Bring the motor back to its previous position
            servo.angle = 0

    # Display the resulting frame
    cv2.imshow('Video', frame)

    # Break the loop on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the webcam and close the OpenCV window
video_capture.release()
cv2.destroyAllWindows()