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

    def continuous_audio_loop(self, stop_event):
        """Runs continuous VAD loop; emits update_signal (thread-safe) for UI updates."""
        def handle_segment(wav_path):
            self.update_signal.emit("Transcribing...")
            text = audio.transcribe_audio(wav_path)
            if text:
                self.update_signal.emit(f"Heard: '{text}'\nAnalyzing with LLM...")
                result = llm.process_text_query(text)
                self.update_signal.emit(f"Answer:\n{result}")

        audio.listen_continuously(handle_segment, stop_event)


class AppController:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = ui.OverlayWindow()

        self.worker = Worker()
        self.worker.update_signal.connect(self.window.update_text)

        self._audio_stop: threading.Event | None = None
        self._audio_thread: threading.Thread | None = None

        # Connect UI buttons
        self.window.btn_screen.clicked.connect(
            lambda: threading.Thread(target=self.worker.process_screen, daemon=True).start()
        )
        self.window.btn_audio.clicked.connect(self.toggle_audio)

        # Keyboard hotkeys
        self.kb_thread = threading.Thread(target=self.setup_hotkeys, daemon=True)
        self.kb_thread.start()

    def toggle_audio(self):
        if self._audio_thread and self._audio_thread.is_alive():
            # --- stop ---
            self._audio_stop.set()
            self.window.btn_audio.setText("🎙  Listen Audio")
            self.window.update_text("Continuous listening **stopped**.")
        else:
            # --- start ---
            self._audio_stop = threading.Event()
            stop_event = self._audio_stop

            self._audio_thread = threading.Thread(
                target=self.worker.continuous_audio_loop,
                args=(stop_event,),
                daemon=True,
            )
            self._audio_thread.start()
            self.window.btn_audio.setText("⏹  Stop Listening")
            self.window.update_text("🎙 Listening continuously...\nWill respond on every pause in speech.")

    def setup_hotkeys(self):
        keyboard.add_hotkey('ctrl+shift+s', lambda: threading.Thread(target=self.worker.process_screen, daemon=True).start())
        keyboard.add_hotkey('ctrl+shift+a', lambda: self.toggle_audio())
        keyboard.add_hotkey('ctrl+shift+h', lambda: self.window.toggle_signal.emit())
        keyboard.add_hotkey('ctrl+c', lambda: self.window.click_through_signal.emit())
        keyboard.wait()

    def run(self):
        if not llm.init_llm():
            self.window.update_text("**Error:** `GOOGLE_API_KEY` environment variable not set.\nPlease set it and restart.")
        self.window.show()
        sys.exit(self.app.exec())

if __name__ == '__main__':
    controller = AppController()
    controller.run()
