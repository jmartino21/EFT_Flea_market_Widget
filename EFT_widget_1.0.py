import tkinter as tk
from tkinter import Label
from PIL import Image, ImageTk
import win32clipboard
import io
import pytesseract
import requests
import random
import os
import sys
import threading
from io import BytesIO
import time

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

MAX_IMAGE_WIDTH = 400 # Adjust as needed
MAX_IMAGE_HEIGHT = 300  # Adjust as needed

def monitor_clipboard():
    previous_image = None
    while True:
        try:
            win32clipboard.OpenClipboard()
            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
                data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
                image = Image.open(io.BytesIO(data))
                if image != previous_image:
                    previous_image = image
                    root.event_generate('<<NewClipboardImage>>', when='tail')
        except Exception as e:
            print(f"Clipboard monitoring error: {e}")
        finally:
            win32clipboard.CloseClipboard()
        time.sleep(2)

def trigger_clipboard_event():
    root.event_generate('<<NewClipboardImage>>', when='tail')

def perform_ocr(image):
    # Convert the image to text
    text = pytesseract.image_to_string(image)
    return text

def get_item_info(item_name):
    api_key = read_api_key()
    if not api_key:
        print("API key not set. Please check config.txt")
        return None
    url = f"https://api.tarkov-market.app/api/v1/item?q={item_name}"
    headers = {'x-api-key': api_key}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data
    else:
        return f"Error: {response.status_code}"

def display_icon_image(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes
        image_data = BytesIO(response.content)
        img = Image.open(image_data)
        img.thumbnail((100, 100))  # Resize the image if necessary
        img_photo = ImageTk.PhotoImage(img)

        icon_label.config(image=img_photo)
        icon_label.image = img_photo  # Keep a reference
    except Exception as e:
        print(f"Error fetching icon image: {e}")



def get_image_from_clipboard():
    try:
        win32clipboard.OpenClipboard()
        opened_clipboard = True

        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
            data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
            image = Image.open(io.BytesIO(data))
            
            # Check image size
            if image.width > MAX_IMAGE_WIDTH or image.height > MAX_IMAGE_HEIGHT:
                error_message_label.config(text="Image too large. Please try again with a smaller image.")
                return
            error_message_label.config(text="")
            
            # Convert the image to a more common format like PNG
            with io.BytesIO() as output:
                image.save(output, format="PNG")
                data = output.getvalue()
                image = Image.open(io.BytesIO(data))

            photo = ImageTk.PhotoImage(image)
            image_label.config(image=photo)
            image_label.image = photo

            extracted_text = perform_ocr(image).strip()
            text_area.delete('1.0', tk.END)
            text_area.insert(tk.END, extracted_text)

            # Use extracted text to get item info
            item_info = get_item_info(extracted_text)
            if item_info:
                first_item = item_info[0]
                avg_24h_price = first_item.get('avg24hPrice')
                if avg_24h_price is not None:
                    formatted_price = f"₽{avg_24h_price:,}"
                    price_area.delete('1.0', tk.END)
                    price_area.insert(tk.END, formatted_price)
                else:
                    price_area.delete('1.0', tk.END)
                    price_area.insert(tk.END, "Price not available")
                    
                # Retrieve and display the icon image
                icon_url = first_item.get('icon')
                if icon_url:
                    display_icon_image(icon_url)
                else:
                    # You can handle the absence of an icon URL here
                    print("Icon URL not found")
            else:
                price_area.delete('1.0', tk.END)
                price_area.insert(tk.END, "Item not found")
                
            

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'opened_clipboard' in locals() and opened_clipboard:
            win32clipboard.CloseClipboard()

def read_api_key(config_file='config.txt'):
    try:
        with open(config_file, 'r') as file:
            lines = file.readlines()
            for line in lines:
                if line.startswith('api_key='):
                    return line.strip().split('=')[1]
    except FileNotFoundError:
        print(f"Configuration file '{config_file}' not found.")
    except Exception as e:
        print(f"Error reading '{config_file}': {e}")
    return None

root = tk.Tk()
root.title("EFT Flea Market Widget")
root.geometry("400x350")

api_key = read_api_key()
if not api_key:
    print("Please enter a valid API key in config.txt")
    sys.exit(1)
# Determine if we're running in a bundled executable (like a PyInstaller .exe)
# Check if we're running in a bundled executable
if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

# Construct paths to the images
image_files = ['bg1.png', 'bg2.png','bg3.png','bg4.png','bg5.png']  # Add all your image filenames here
image_paths = [os.path.join(application_path, 'images', filename) for filename in image_files]

# Randomly select an image
selected_image_path = random.choice(image_paths)
bg_image = Image.open(selected_image_path)
bg_photo = ImageTk.PhotoImage(bg_image)

# Create a label with the image
bg_label = Label(root, image=bg_photo)
bg_label.place(x=0, y=0, relwidth=1, relheight=1)  # This makes the label cover the whole window

image_label = tk.Label(root)
image_label.pack()

text_area = tk.Text(root, height=1, width=15,font="Times 12 bold",bg = 'gray')
text_area.pack()

# Create a Label as a title for the Text widget
title_label = tk.Label(root, text="24-hour Average Price",font="Times 14 bold", bg="lightgray")
title_label.pack()


# Add an area to display the price info
price_area = tk.Text(root, height=1, width=15,font="Times 12 bold", bg = 'gray')
price_area.pack()

icon_label = tk.Label(root)
icon_label.pack() 

error_message_label = tk.Label(root, text="", fg="red")  # 'fg' sets the font color to red
error_message_label.pack()

# Add a Label for instructions at the bottom
instructions = "How to Use: Start with the Snipping Tool ( Windows + LShift + S) to select the items name that you are wondering the price of and click 'Get Iamge from Clipboard' to upload it"
instruction_label = tk.Label(root, text=instructions, bg="lightgray", wraplength=300, justify="center")
instruction_label.pack(side="bottom", fill="x", padx=15, pady=15)

root.bind('<<NewClipboardImage>>', lambda e: get_image_from_clipboard())

clipboard_monitor_thread = threading.Thread(target=monitor_clipboard, daemon=True)
clipboard_monitor_thread.start()

root.mainloop()