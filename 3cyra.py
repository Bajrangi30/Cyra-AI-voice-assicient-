"""
CYRA - Tkinter (CustomTkinter) GUI Voice Assistant (Option 1)
Features:
- Modern UI using customtkinter
- Uses uploaded image at /mnt/data/Screenshot 2025-11-19 233205.png as background
- Speech-to-text (Google) via speech_recognition
- Text-to-speech via pyttsx3
- Thread-safe listening (non-blocking)
- Hinglish / English / Hindi reply modes
- Simple CYRA brain (open google/youtube, time, greetings)
"""

import threading
import webbrowser
import datetime
import os
import sys
import time
import traceback

import customtkinter as ctk
from PIL import Image, ImageTk

# Speech libraries
import speech_recognition as sr
import pyttsx3

# ---------------------- Configuration ----------------------
BACKGROUND_IMAGE_PATH = "/mnt/data/Screenshot 2025-11-19 233205.png"  # change if needed
WINDOW_TITLE = "CYRA - Voice Assistant (CustomTkinter)"
WINDOW_SIZE = "1000x700"

# ---------------------- Initialize TTS -----------------------
engine = pyttsx3.init()
# voice selection (try to pick an Indian English-like voice if available)
voices = engine.getProperty("voices")
# select first voice by default
if voices:
    engine.setProperty("voice", voices[0].id)
engine.setProperty("rate", 170)  # speaking speed

def speak(text, lang_mode="hinglish"):
    """
    Speak text (non-blocking)
    lang_mode kept for future adjustment (pitch/rate)
    """
    def _s():
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception:
            # fallback silent
            print("TTS error:", traceback.format_exc())
    threading.Thread(target=_s, daemon=True).start()

# ---------------------- Speech Recognition ------------------
recognizer = sr.Recognizer()
mic = None
# pick default microphone index if multiple microphones exist — use sr.Microphone() default

# ---------------------- CYRA Brain --------------------------
def cyra_brain(text, mode):
    t = text.lower()
    # greetings
    if any(k in t for k in ("hello", "hi cyra", "hey cyra", "hello cyra")):
        if mode == "hinglish":
            return "Haan bhaiya, main sun rahi hoon. Bataiye kya karna hai?"
        if mode == "hindi":
            return "Haan bhaiya, main sun rahi hoon. क्या चाहिए?"
        return "Hello bhaiya, I am listening. How can I help?"
    # time
    if "time" in t or "kya time" in t or "samay" in t:
        now = datetime.datetime.now()
        hh = now.hour
        mm = now.minute
        if mode == "hinglish":
            return f"Abhi ka time {hh}:{mm:02d} hai."
        if mode == "hindi":
            return f"Abhi samay {hh} bajkar {mm} minute hai."
        return f"The current time is {hh}:{mm:02d}."
    # open google
    if "google" in t and ("open" in t or "khol" in t):
        return "open_google"
    # open youtube
    if "youtube" in t or ("open" in t and "video" in t):
        return "open_youtube"
    # translate hello example
    if "translate" in t and "hello" in t:
        if mode in ("hinglish", "hindi"):
            return 'Hello ka hindi mein matlab hai: "Namaste".'
        return 'Translation: "Hello" in Hindi is "Namaste".'
    # help
    if "help" in t or "what can you" in t or "kya kar sakti" in t:
        if mode == "hinglish":
            return "Main Google/YouTube open kar sakti hoon, time bata sakti hoon, aur kuch basic commands handle kar sakti hoon."
        if mode == "hindi":
            return "Main Google/YouTube खोल सकती हूँ, समय बता सकती हूँ और कुछ commands handle कर सकती हूँ."
        return "I can open Google/YouTube, tell time, and handle basic commands."
    # fallback
    if mode == "hinglish":
        return "Maaf kijiye bhaiya, main isse samajh nahi paayi. Thoda phir se bolo."
    if mode == "hindi":
        return "माफ कीजिये, मैं समझ नहीं पायी। फिर से कहिये।"
    return "Sorry, I didn't catch that. Please say it again."

# ---------------------- GUI App -----------------------------
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class CyraApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # state
        self.listening = False
        self.listen_thread = None
        self.selected_mode = ctk.StringVar(value="hinglish")  # hinglish / english / hindi

        # layout frames
        self.create_widgets()

    def create_widgets(self):
        # left: big sphere + status
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.pack(side="left", padx=20, pady=20, fill="both", expand=False)

        # try to load background image if exists
        img_label = None
        try:
            if os.path.exists(BACKGROUND_IMAGE_PATH):
                pil = Image.open(BACKGROUND_IMAGE_PATH).convert("RGBA")
                # resize to a square for hero (keep decent size)
                pil = pil.resize((420,420), Image.LANCZOS)
                self.bg_img = ImageTk.PhotoImage(pil)
                img_label = ctk.CTkLabel(left_frame, image=self.bg_img, text="")
                img_label.pack(pady=8)
            else:
                # fallback: draw gradient-like circle via canvas
                canvas = ctk.CTkCanvas(left_frame, width=420, height=420, highlightthickness=0)
                canvas.pack(pady=8)
                # simple circle (visual only)
                canvas.create_oval(10,10,410,410, fill="#1f134b", outline="#6b3fe6", width=4)
        except Exception as e:
            print("Image load error:", e)
            canvas = ctk.CTkCanvas(left_frame, width=420, height=420, highlightthickness=0)
            canvas.pack(pady=8)
            canvas.create_oval(10,10,410,410, fill="#1f134b", outline="#6b3fe6", width=4)

        # status label
        self.status_label = ctk.CTkLabel(left_frame, text="CYRA Ready", font=ctk.CTkFont(size=16, weight="bold"))
        self.status_label.pack(pady=(12,0))

        # waveform simulation bars
        self.bars_frame = ctk.CTkFrame(left_frame, width=420, height=40, fg_color="transparent")
        self.bars_frame.pack(pady=(12,0))
        self.bar_rects = []
        for i in range(18):
            b = ctk.CTkFrame(self.bars_frame, width=14, height=24, fg_color="#5be1ff")
            b.pack(side="left", padx=3, pady=4)
            self.bar_rects.append(b)
        self.animate_bars_running = False

        # right frame: controls + transcript
        right_frame = ctk.CTkFrame(self)
        right_frame.pack(side="right", padx=20, pady=20, fill="both", expand=True)

        title = ctk.CTkLabel(right_frame, text="CYRA — Voice Controlled Assistant", font=ctk.CTkFont(size=18, weight="bold"))
        title.pack(pady=(6,6))

        # mode selector
        mode_box = ctk.CTkComboBox(right_frame, values=["hinglish","english","hindi"], variable=self.selected_mode, width=200)
        mode_box.pack(pady=(4,4))
        mode_box.set("hinglish")

        # you said box
        self.you_box = ctk.CTkTextbox(right_frame, height=80)
        self.you_box.insert("0.0", "You said: —")
        self.you_box.configure(state="disabled")
        self.you_box.pack(fill="x", pady=(12,6))

        # cyra reply box
        self.reply_box = ctk.CTkTextbox(right_frame, height=120)
        self.reply_box.insert("0.0", "CYRA: Hello bhaiya — click mic and speak.")
        self.reply_box.configure(state="disabled")
        self.reply_box.pack(fill="both", pady=(6,12), expand=True)

        # controls row
        ctrl_frame = ctk.CTkFrame(right_frame)
        ctrl_frame.pack(pady=8)

        self.mic_btn = ctk.CTkButton(ctrl_frame, text="🎙️ Start Listening", command=self.toggle_listen, width=180, fg_color="#2563EB")
        self.mic_btn.grid(row=0, column=0, padx=8, pady=6)

        self.stop_btn = ctk.CTkButton(ctrl_frame, text="Stop", command=self.stop_listen, width=80, fg_color="#DC2626")
        self.stop_btn.grid(row=0, column=1, padx=8, pady=6)

        # small footer
        footer = ctk.CTkLabel(right_frame, text="Tip: Use clear voice. Desktop encryption available in Python version.", font=ctk.CTkFont(size=11))
        footer.pack(side="bottom", pady=8)

    # animate bars when listening
    def animate_bars(self):
        self.animate_bars_running = True
        def run():
            while self.animate_bars_running:
                for i, b in enumerate(self.bar_rects):
                    h = 10 + int(abs((time.time()*5 + i) % 6) * (i % 6 + 2))
                    # change height via geometry (approx by configure size)
                    try:
                        b.configure(height=max(6, h))
                    except Exception:
                        pass
                time.sleep(0.12)
        threading.Thread(target=run, daemon=True).start()

    def stop_animate_bars(self):
        self.animate_bars_running = False
        # reset bars
        for b in self.bar_rects:
            try:
                b.configure(height=18)
            except Exception:
                pass

    # start/stop listening
    def toggle_listen(self):
        if not self.listening:
            self.start_listen_thread()
        else:
            self.stop_listen()

    def start_listen_thread(self):
        self.listening = True
        self.mic_btn.configure(text="🔴 Listening...")
        self.status_label.configure(text="Listening...")
        self.you_box.configure(state="normal")
        self.you_box.delete("0.0", "end")
        self.you_box.insert("0.0", "You said: —")
        self.you_box.configure(state="disabled")
        # animate bars
        self.animate_bars()
        self.listen_thread = threading.Thread(target=self.listen_and_process, daemon=True)
        self.listen_thread.start()

    def stop_listen(self):
        self.listening = False
        self.mic_btn.configure(text="🎙️ Start Listening")
        self.status_label.configure(text="CYRA Ready")
        self.stop_animate_bars()

    def listen_and_process(self):
        # This runs in background thread (non-blocking mainloop)
        try:
            with sr.Microphone() as source:
                # adjust energy threshold a bit
                recognizer.adjust_for_ambient_noise(source, duration=0.8)
                audio = recognizer.listen(source, timeout=6, phrase_time_limit=8)
                # after capturing, set listening false to reset UI
                # convert to text
                try:
                    text = recognizer.recognize_google(audio, language="en-IN")
                except sr.RequestError:
                    text = None
                    self.safe_update_reply("Network error: Please check your internet for speech recognition.")
                except sr.UnknownValueError:
                    text = None
                    self.safe_update_reply("Sorry bhaiya, I couldn't understand. Try again.")
                if text:
                    # update you said
                    self.safe_update_you(f"You said: {text}")
                    # brain
                    mode = self.selected_mode.get()
                    reply = cyra_brain(text, mode)
                    # actions
                    if reply == "open_google":
                        self.safe_update_reply("Opening Google...")
                        speak("Theek hai, Google khol raha hoon.", mode)
                        webbrowser.open("https://www.google.com")
                    elif reply == "open_youtube":
                        self.safe_update_reply("Opening YouTube...")
                        speak("YouTube khol raha hoon.", mode)
                        webbrowser.open("https://www.youtube.com")
                    else:
                        self.safe_update_reply(reply)
                        # speak
                        # choose TTS text slight variations for Hinglish
                        if mode == "hinglish":
                            speak(reply, mode)
                        elif mode == "hindi":
                            speak(reply, mode)
                        else:
                            speak(reply, mode)
        except sr.WaitTimeoutError:
            self.safe_update_reply("Listening timeout. Try again.")
        except Exception as e:
            print("Listen thread error:", e)
            traceback.print_exc()
            self.safe_update_reply("Error during listening. Check microphone or permissions.")
        finally:
            # reset UI state
            self.listening = False
            self.mic_btn.configure(text="🎙️ Start Listening")
            self.status_label.configure(text="CYRA Ready")
            self.stop_animate_bars()

    # thread-safe UI updates
    def safe_update_you(self, text):
        def _u():
            self.you_box.configure(state="normal")
            self.you_box.delete("0.0", "end")
            self.you_box.insert("0.0", text)
            self.you_box.configure(state="disabled")
        self.after(1, _u)

    def safe_update_reply(self, text):
        def _r():
            self.reply_box.configure(state="normal")
            self.reply_box.delete("0.0", "end")
            self.reply_box.insert("0.0", "CYRA: " + text)
            self.reply_box.configure(state="disabled")
        self.after(1, _r)

    def on_close(self):
        # cleanup
        try:
            self.listening = False
        except:
            pass
        self.destroy()

# ---------------------- Run app -----------------------------
if __name__ == "__main__":
    app = CyraApp()
    # greeting
    app.safe_update_reply("CYRA initialized. Click Start Listening and say 'Hello Cyra'.")
    speak("Hello bhaiya, main CYRA hoon. Aap bol sakte hain.")
    app.mainloop()
