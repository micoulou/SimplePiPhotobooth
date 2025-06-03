#!/usr/bin/python3
import tkinter as tk
from PIL import Image, ImageTk,  ImageDraw, ImageFont
from picamera2 import Picamera2
from datetime import datetime
import subprocess
import os
import time
import threading
from gpiozero import Button, LED, TonalBuzzer

# === CONFIGURATION ===
PHOTO_DIR = "/home/mikey/photos"
os.makedirs(PHOTO_DIR, exist_ok=True)
last_photo = None
CAPTURE_BUTTON = Button(26)
PRINT_BUTTON = Button(19)
LEDRED = LED(5)
BuzzerSound = TonalBuzzer (11)
POWEROFF_BUTTON = Button(22)

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480)}))
picam2.start()

# === INTERFACE TKINTER ===
window = tk.Tk()
window.attributes('-fullscreen', True)  # plein écran
window.bind('<Escape>', lambda e: window.destroy())  # pour sortir avec ESC
window.bind('<Key>', lambda e: window.destroy() if e.char.lower() == 'q' else None)  # touche q
window.title("Photobooth")
window.geometry("1024x600")
window.configure(bg='black')
bg_image = Image.open("cadre_mariage.jpg")
bg_photo = ImageTk.PhotoImage(bg_image)
bg_label = tk.Label(window, image=bg_photo)
bg_label.place(x=0, y=0, relwidth=1, relheight=1)

preview_label = tk.Label(window)
preview_label.pack()

countdown_label = tk.Label(window, text="", font=("Helvetica", 72), fg="white", bg="black")
countdown_label.place(relx=0.5, rely=0.4, anchor=tk.CENTER)

def compose_print_image(photo_path):
    # Ouvre la photo et la convertit en N&B
    base_photo = Image.open(photo_path).convert("L")
    base_photo = base_photo.resize((384, 400))  # Largeur max de la plupart des imprimantes thermiques

    # Crée une image plus grande pour ajouter cadre + texte
    width, height = 384, 480
    framed = Image.new("L", (width, height), "white")
    draw = ImageDraw.Draw(framed)

    # Ajoute la photo au centre
    framed.paste(base_photo, (0, 60))

    # Ajoute texte en haut
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    except:
        font = ImageFont.load_default()

    draw.text((width // 2, 10), "Mariage Paula and Heath", fill="black", anchor="mm", font=font)
    draw.text((width // 2, 35), "15 juin 2025", fill="black", anchor="mm", font=font)
    framed.paste(base_photo, (0, 60))
    # Enregistre l’image finale
    framed_path = photo_path.replace(".jpg", "_framed.png")
    framed.save(framed_path)
    #framed = ImageOps.autocontrast(framed, cutoff=3)

    pbm_image = framed.convert("1")  # Binaire pur (1-bit)
    pbm_path = photo_path.replace(".jpg", ".pbm")
    pbm_image.save(pbm_path)

    return pbm_path

# === ACTUALISER LA PREVIEW CAMERA ===
def update_preview():
    frame = picam2.capture_array()
    image = Image.fromarray(frame)
    image = image.resize((800, 600))
    photo = ImageTk.PhotoImage(image)
    preview_label.config(image=photo)
    preview_label.image = photo
    window.after(30, update_preview)

# === COMPTE À REBOURS ===
def countdown(n=3):
    countdown_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
    for i in range(n, 0, -1):
        countdown_label.config(text=str(i))
        time.sleep(1)
    countdown_label.config(text="📸")
    BuzzerSound.play(60)
    time.sleep(0.05)
    BuzzerSound.stop()
    time.sleep(0.5)
    countdown_label.config(text="")
    countdown_label.place_forget()

# === PRENDRE UNE PHOTO ===
def take_photo():
    global last_photo
    threading.Thread(target=_take_photo).start()

def _take_photo():
    global last_photo
    countdown()
    filename = f"photo_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
    filepath = os.path.join(PHOTO_DIR, filename)
    picam2.capture_file(filepath)
    print(f"[✅] Photo enregistrée : {filepath}")
    last_photo = filepath
    print(last_photo)

# === IMPRIMER LA PHOTO ===
def print_photo():
    global last_photo
    if last_photo and os.path.exists(last_photo):
        print("[🖨️] Génération avec cadre...")
        pbm_file = compose_print_image(last_photo)
        print(pbm_file)
        subprocess.run(["/home/mikey/Cat-Printer/printer.py", "-s", "5,MX10", pbm_file], cwd="/home/mikey/Cat-Printer")
    else:
        print("[⚠️] Aucune photo à imprimer.")

# === BOUTONS ===
# Bouton capture (rond rouge)
photo_btn = tk.Button(window, text="●", font=("Helvetica", 48), fg="red", bg="black", bd=0, command=take_photo)
photo_btn.place(relx=0.3, rely=0.85, anchor=tk.CENTER)

# Bouton impression (icône imprimante)
iconImage=Image.open("imprimante.png")
icon=ImageTk.PhotoImage(iconImage)
print_btn = tk.Button(window, text="🖨️", font=("Helvetica", 40), image=icon, fg="white", bg="black", bd=0, command=print_photo)
print_btn.place(relx=0.7, rely=0.85, anchor=tk.CENTER)

# === LANCEMENT ===
update_preview()
CAPTURE_BUTTON.when_pressed = take_photo
PRINT_BUTTON.when_pressed = print_photo
window.mainloop()

