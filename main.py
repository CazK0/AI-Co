import tkinter as tk
import ctypes
import threading
from audio import AudioRecorder
from screenshot import ScreenCapturer
from ai_engine import AIEngine


class CopilotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Copilot UI")
        self.root.geometry("500x600")
        self.root.attributes("-topmost", True)

        self.recorder = AudioRecorder()
        self.capturer = ScreenCapturer()
        self.ai = AIEngine()

        self.set_stealth_mode()
        self.create_widgets()

    def set_stealth_mode(self):
        self.root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)

    def create_widgets(self):
        self.text_area = tk.Text(self.root, wrap=tk.WORD, font=("Arial", 12))
        self.text_area.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        self.text_area.insert(tk.END, "System ready...\n")
        self.text_area.config(state=tk.DISABLED)

        self.btn_frame = tk.Frame(self.root)
        self.btn_frame.pack(fill=tk.X, padx=10, pady=10)

        self.start_btn = tk.Button(self.btn_frame, text="Start Recording", command=self.start_audio)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(self.btn_frame, text="Stop", command=self.stop_audio, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.screen_btn = tk.Button(self.btn_frame, text="Screenshot", command=self.take_screenshot)
        self.screen_btn.pack(side=tk.LEFT, padx=5)

        self.transcribe_btn = tk.Button(self.btn_frame, text="Transcribe", command=self.process_transcription)
        self.transcribe_btn.pack(side=tk.LEFT, padx=5)

    def log(self, message):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, f"{message}\n\n")
        self.text_area.config(state=tk.DISABLED)
        self.text_area.see(tk.END)

    def start_audio(self):
        self.recorder.start_recording()
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.log("Recording audio...")

    def stop_audio(self):
        self.recorder.stop_recording()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.log("Audio saved to output.wav")

    def take_screenshot(self):
        filename = self.capturer.capture()
        self.log(f"Screenshot saved to {filename}")

    def process_transcription(self):
        self.transcribe_btn.config(state=tk.DISABLED)
        self.log("Sending audio to Whisper API...")
        threading.Thread(target=self._run_transcription, daemon=True).start()

    def _run_transcription(self):
        result = self.ai.transcribe_audio("output.wav")
        self.root.after(0, self._transcription_done, result)

    def _transcription_done(self, result):
        self.log(f"Interviewer: {result}")
        self.transcribe_btn.config(state=tk.NORMAL)


def main():
    root = tk.Tk()
    app = CopilotApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()