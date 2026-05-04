import sys
import threading
import keyboard
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import pyqtSignal, QObject


import ui
import vision
import llm
import audio

class Worker(QObject):
    update_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def process_screen(self):
        self.update_signal.emit("Capturing screen...")
        img_path = vision.capture_screen()
        if img_path:
            self.update_signal.emit("Analyzing screen with LLM...")
            result = llm.process_vision_query(img_path)
            self.update_signal.emit(f"Answer:\n{result}")
        else:
            self.update_signal.emit("Failed to capture screen.")

    def process_audio(self):
        self.update_signal.emit("Listening to system audio (5s)...")
        wav_path = audio.record_system_audio(duration=5)
        if wav_path:
            self.update_signal.emit("Transcribing audio...")
            text = audio.transcribe_audio(wav_path)
            if text:
                self.update_signal.emit(f"Heard: '{text}'\nAnalyzing with LLM...")
                result = llm.process_text_query(text)
                self.update_signal.emit(f"Answer:\n{result}")
            else:
                self.update_signal.emit("No speech detected or could not understand.")
        else:
            self.update_signal.emit("Failed to capture audio.")

class AppController:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = ui.OverlayWindow()
        
        self.worker = Worker()
        self.worker.update_signal.connect(self.window.update_text)

        # Connect UI buttons to worker methods
        self.window.btn_screen.clicked.connect(
            lambda: threading.Thread(target=self.worker.process_screen, daemon=True).start()
        )
        self.window.btn_audio.clicked.connect(
            lambda: threading.Thread(target=self.worker.process_audio, daemon=True).start()
        )

        # Start keyboard listener in a separate thread
        self.kb_thread = threading.Thread(target=self.setup_hotkeys, daemon=True)
        self.kb_thread.start()

    def setup_hotkeys(self):
        # Register Hotkeys
        # Ctrl+Shift+S -> Capture Screen
        # Ctrl+Shift+A -> Capture Audio
        # Ctrl+Shift+H -> Toggle visibility
        keyboard.add_hotkey('ctrl+shift+s', lambda: threading.Thread(target=self.worker.process_screen, daemon=True).start())
        keyboard.add_hotkey('ctrl+shift+a', lambda: threading.Thread(target=self.worker.process_audio, daemon=True).start())
        keyboard.add_hotkey('ctrl+shift+h', lambda: self.window.toggle_signal.emit())
        keyboard.add_hotkey('ctrl+alt+c', lambda: self.window.click_through_signal.emit())
        keyboard.wait() # Block forever in this thread

    def run(self):
        # Init LLM
        if not llm.init_llm():
            self.window.update_text("**Error:** `GOOGLE_API_KEY` environment variable not set.\nPlease set it and restart.")
        self.window.show()
        sys.exit(self.app.exec())

if __name__ == '__main__':
    controller = AppController()
    controller.run()
