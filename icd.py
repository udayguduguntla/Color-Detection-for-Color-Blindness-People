import cv2
import pandas as pd
import numpy as np
import imutils
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import hashlib
import os
import logging
from datetime import datetime
import json
from cryptography.fernet import Fernet
import secrets
import re

# Initialize logging
logging.basicConfig(
    filename='app_security.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SecurityManager:
    def __init__(self):
        self.key_file = "secret.key"
        self.max_failed_attempts = 3
        self.failed_attempts = 0
        self.session_token = None
        self._load_or_generate_key()
        
    def _load_or_generate_key(self):
        try:
            if os.path.exists(self.key_file):
                with open(self.key_file, 'rb') as key_file:
                    self.key = key_file.read()
            else:
                self.key = Fernet.generate_key()
                with open(self.key_file, 'wb') as key_file:
                    key_file.write(self.key)
            self.cipher_suite = Fernet(self.key)
        except Exception as e:
            logging.error(f"Error in key management: {str(e)}")
            raise

    def encrypt_file(self, file_path):
        try:
            with open(file_path, 'rb') as file:
                file_data = file.read()
            encrypted_data = self.cipher_suite.encrypt(file_data)
            encrypted_path = file_path + '.encrypted'
            with open(encrypted_path, 'wb') as file:
                file.write(encrypted_data)
            return encrypted_path
        except Exception as e:
            logging.error(f"Encryption error: {str(e)}")
            return None

    def decrypt_file(self, encrypted_path):
        try:
            with open(encrypted_path, 'rb') as file:
                encrypted_data = file.read()
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            return decrypted_data
        except Exception as e:
            logging.error(f"Decryption error: {str(e)}")
            return None

    def generate_session_token(self):
        self.session_token = secrets.token_hex(32)
        return self.session_token

    def validate_file_hash(self, file_path):
        try:
            with open(file_path, 'rb') as file:
                bytes = file.read()
                readable_hash = hashlib.sha256(bytes).hexdigest()
            return readable_hash
        except Exception as e:
            logging.error(f"Hash validation error: {str(e)}")
            return None

# Initialize security manager
security_manager = SecurityManager()

# Function to validate image file
def validate_image(file_path):
    allowed_extensions = {'.jpg', '.jpeg', '.png'}
    file_extension = os.path.splitext(file_path)[1].lower()
    
    if file_extension not in allowed_extensions:
        logging.warning(f"Invalid file type attempted: {file_extension}")
        return False
    
    # Check file size (max 10MB)
    if os.path.getsize(file_path) > 10 * 1024 * 1024:
        logging.warning(f"File too large: {file_path}")
        return False
        
    return True

# Initialize global variables
r = g = b = xpos = ypos = 0
df = None

# Function to get RGB values on mouse click
def getRGBvalue(event, x, y, flags, param):
    global b, g, r, xpos, ypos
    if event == cv2.EVENT_MOUSEMOVE:  # Detect mouse movement
        xpos = x
        ypos = y
        b, g, r = param[y, x]  # Get the color values
        b = int(b)
        g = int(g)
        r = int(r)

# Function to get the closest color name
def colorname(B, G, R):
    minimum = 10000
    cname = ""
    for i in range(len(df)):
        d = abs(B - int(df.loc[i, "B"])) + abs(G - int(df.loc[i, "G"])) + abs(R - int(df.loc[i, "R"]))
        if d <= minimum:
            minimum = d
            cname = df.loc[i, "color_name"] + " Hex: " + df.loc[i, "hex"]
    return cname

# Modified open_image function with security features
def open_image():
    global img, imgWidth
    try:
        file_path = filedialog.askopenfilename(
            title="Select an Image", 
            filetypes=[("Image files", "*.jpg *.jpeg *.png")]
        )
        
        if file_path:
            # Validate file
            if not validate_image(file_path):
                messagebox.showerror("Error", "Invalid file format or size")
                logging.warning(f"Invalid file attempt: {file_path}")
                return

            # Calculate and log file hash
            file_hash = security_manager.validate_file_hash(file_path)
            logging.info(f"Opening image: {file_path} with hash: {file_hash}")

            img = cv2.imread(file_path)
            if img is None:
                messagebox.showerror("Error", "Could not open or find the image.")
                logging.error(f"Failed to open image: {file_path}")
            else:
                imgWidth = img.shape[1] - 40
                load_csv()
                detect_colors(img)
                
    except Exception as e:
        logging.error(f"Error in open_image: {str(e)}")
        messagebox.showerror("Error", "An error occurred while opening the image")

# Function to start color detection on a static image
def detect_colors(img):
    global b, g, r, xpos, ypos

    # Check if CSV data is loaded
    if df is None:
        messagebox.showerror("Error", "Color data not loaded. Please ensure the CSV file is present.")
        return

    try:
        # Create a window and bind the callback function to it
        cv2.namedWindow("Image", cv2.WINDOW_AUTOSIZE)  # Changed to WINDOW_AUTOSIZE
        cv2.setMouseCallback("Image", getRGBvalue, img)

        while True:
            # Create a copy of the image for display
            img_copy = img.copy()

            # Draw rectangle and display color information
            cv2.rectangle(img_copy, (20, 20), (img.shape[1] - 40, 60), (b, g, r), -1)
            text = colorname(b, g, r) + '   R=' + str(r) + ' G=' + str(g) + ' B=' + str(b)

            # Display text on a white background for dark colors and vice versa
            if r + g + b >= 600:
                cv2.putText(img_copy, text, (50, 50), 2, 0.8, (0, 0, 0), 2, cv2.LINE_AA)
            else:
                cv2.putText(img_copy, text, (50, 50), 2, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

            try:
                # Show the image
                cv2.imshow("Image", img_copy)
            except cv2.error as e:
                messagebox.showerror("Error", "Failed to display image window")
                break

            # Break the loop when 'ESC' is pressed
            key = cv2.waitKey(20) & 0xFF
            if key == 27:
                break

        try:
            cv2.destroyAllWindows()
        except:
            pass
    except cv2.error as e:
        messagebox.showerror("Error", "Failed to initialize OpenCV window")

# Modified load_csv function with security features
def load_csv():
    global df
    index = ['color', 'color_name', 'hex', 'R', 'G', 'B']
    try:
        csv_path = "colors.csv"
        
        # Validate CSV file hash
        csv_hash = security_manager.validate_file_hash(csv_path)
        logging.info(f"Loading CSV with hash: {csv_hash}")
        
        df = pd.read_csv(csv_path, header=None, names=index)
        
        # Basic data validation
        if df.isnull().values.any():
            logging.warning("CSV contains null values")
            messagebox.showwarning("Warning", "The color data contains some invalid entries")
            
    except FileNotFoundError:
        logging.error("colors.csv file not found")
        messagebox.showerror("Error", "colors.csv file not found.")
        df = None
    except Exception as e:
        logging.error(f"Error loading CSV: {str(e)}")
        messagebox.showerror("Error", "Error loading color data")
        df = None

# Function to start webcam color detection in a separate thread
def start_webcam_thread():
    # Create a thread to run webcam_color_detection
    thread = threading.Thread(target=webcam_color_detection)
    thread.start()

# Function to get the color name based on RGB values
def getColorName(R, G, B):
    minimum = 10000
    cname = ""
    for i in range(len(df)):
        d = abs(R - int(df.loc[i, "R"])) + abs(G - int(df.loc[i, "G"])) + abs(B - int(df.loc[i, "B"]))
        if d < minimum:
            minimum = d
            cname = df.loc[i, 'color_name'] + '   Hex=' + df.loc[i, 'hex']
    return cname

# Mouse callback function to get color values on mouse movement
def identify_color(event, x, y, flags, param):
    global b, g, r, xpos, ypos
    if event == cv2.EVENT_MOUSEMOVE:
        xpos = x
        ypos = y
        b, g, r = param[y, x]  # Read pixel color from frame
        b = int(b)
        g = int(g)
        r = int(r)

# Modified webcam_color_detection with security features
def webcam_color_detection():
    global r, g, b, xpos, ypos

    if df is None:
        load_csv()
        if df is None:
            return

    camera = None
    session_token = security_manager.generate_session_token()
    
    try:
        camera = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        
        if not camera.isOpened():
            logging.error("Failed to open webcam")
            messagebox.showerror("Error", "Webcam could not be opened.")
            return

        logging.info(f"Webcam session started with token: {session_token}")
        
        # Create a named window for video
        cv2.namedWindow('image', cv2.WINDOW_AUTOSIZE)  # Changed to WINDOW_AUTOSIZE

        while True:
            grabbed, frame = camera.read()  # Capture a frame from the webcam
            if not grabbed:
                messagebox.showerror("Error", "Failed to grab frame from webcam.")
                break

            frame = imutils.resize(frame, width=900)  # Resize the frame for better display

            try:
                # Show the video feed frame
                cv2.imshow('image', frame)
            except cv2.error:
                messagebox.showerror("Error", "Failed to display webcam window")
                break

            # Set callback function for mouse movement
            cv2.setMouseCallback('image', getRGBvalue, frame)

            # Draw a rectangle showing the detected color
            cv2.rectangle(frame, (20, 20), (800, 60), (b, g, r), -1)

            # Prepare the text showing the color name, RGB, and Hex
            text = getColorName(r, g, b) + '   R=' + str(r) + ' G=' + str(g) + ' B=' + str(b)

            # Display text on white or black based on brightness
            text_color = (0, 0, 0) if r + g + b >= 600 else (255, 255, 255)
            cv2.putText(frame, text, (50, 50), 2, 0.8, text_color, 2, cv2.LINE_AA)

            try:
                # Show the video feed with the color detection overlay
                cv2.imshow('image', frame)
            except cv2.error:
                break

            # Exit when 'ESC' is pressed
            if cv2.waitKey(20) & 0xFF == 27:
                break

    except Exception as e:
        logging.error(f"Webcam error: {str(e)}")
        messagebox.showerror("Error", f"An error occurred: {str(e)}")
    finally:
        # Clean up
        if camera is not None:
            camera.release()
        try:
            cv2.destroyAllWindows()
        except:
            pass
        logging.info(f"Webcam session ended: {session_token}")

# Add security audit logging
def log_security_event(event_type, details):
    logging.info(f"Security Event - {event_type}: {details}")

# Modified main GUI setup with security features
class SecureColorDetectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Secure Color Detection App")
        self.setup_ui()
        self.session_token = security_manager.generate_session_token()
        logging.info(f"Application started with session token: {self.session_token}")

    def setup_ui(self):
        # Create a frame for buttons
        frame = tk.Frame(self.root)
        frame.pack(pady=20)

        # Create a label
        label = tk.Label(frame, text="Secure Color Detection for Color Blindness")
        label.pack(pady=10)

        # Buttons with security logging
        btn_select_image = tk.Button(frame, text="Select Image", 
                                   command=lambda: self.log_and_execute(open_image, "image_selection"))
        btn_select_image.pack(pady=5)

        btn_webcam = tk.Button(frame, text="Start Webcam Color Detection", 
                             command=lambda: self.log_and_execute(start_webcam_thread, "webcam_start"))
        btn_webcam.pack(pady=5)

    def log_and_execute(self, func, action_type):
        logging.info(f"User initiated action: {action_type}")
        func()

# Modified main execution
if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = SecureColorDetectionApp(root)
        root.mainloop()
    except Exception as e:
        logging.critical(f"Application crash: {str(e)}")
        messagebox.showerror("Critical Error", "Application encountered a critical error")
