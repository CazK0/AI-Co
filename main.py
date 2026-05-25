import tkinter as tk
import ctypes
import threading
import keyboard
from audio import AudioRecorder
from screenshot import ScreenCapturer
from ai_engine import AIEngine


class CopilotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Copilot UI")
        self.root.geometry("500x650")
        self.root.attributes("-topmost", True)

        self.recorder = AudioRecorder()
        self.capturer = ScreenCapturer()
        self.ai = AIEngine()

        self._vad_running = False

        self.set_stealth_mode()
        self.create_widgets()
        self.setup_hotkeys()

    def set_stealth_mode(self):
        self.root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
        ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, 0x11)

    def create_widgets(self):
        self.text_area = tk.Text(self.root, wrap=tk.WORD, font=("Arial", 12))
        self.text_area.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        self.text_area.insert(
            tk.END,
            "System ready...\n"
            "Hotkeys:\n"
            "  Ctrl+Alt+R  : Toggle manual recording\n"
            "  Ctrl+Alt+V  : Toggle VAD (auto-detect speech)\n"
            "  Ctrl+Alt+S  : Analyse screen\n\n",
        )
        self.text_area.config(state=tk.DISABLED)

        self.btn_frame = tk.Frame(self.root)
        self.btn_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

        self.start_btn = tk.Button(self.btn_frame, text="Start Recording", command=self.start_audio)
        self.start_btn.pack(side=tk.LEFT, padx=4)

        self.stop_btn = tk.Button(self.btn_frame, text="Stop", command=self.stop_audio, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=4)

        self.transcribe_btn = tk.Button(self.btn_frame, text="Transcribe", command=self.process_transcription)
        self.transcribe_btn.pack(side=tk.LEFT, padx=4)

        self.screen_btn = tk.Button(self.btn_frame, text="Screenshot", command=self.take_screenshot)
        self.screen_btn.pack(side=tk.LEFT, padx=4)

        self.analyze_btn = tk.Button(self.btn_frame, text="Analyse Screen", command=self.process_vision)
        self.analyze_btn.pack(side=tk.LEFT, padx=4)

        self.btn_frame2 = tk.Frame(self.root)
        self.btn_frame2.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.vad_btn = tk.Button(
            self.btn_frame2,
            text="▶ Start VAD",
            command=self.toggle_vad,
            bg="#2ecc71",
            fg="white",
            font=("Arial", 10, "bold"),
        )
        self.vad_btn.pack(side=tk.LEFT, padx=4)

        self.vad_status = tk.Label(self.btn_frame2, text="VAD: Off", font=("Arial", 10), fg="grey")
        self.vad_status.pack(side=tk.LEFT, padx=8)

        self.clear_btn = tk.Button(self.btn_frame2, text="Clear", command=self.clear_log)
        self.clear_btn.pack(side=tk.RIGHT, padx=4)

    def setup_hotkeys(self):
        keyboard.add_hotkey("ctrl+alt+r", self.toggle_audio_from_hotkey)
        keyboard.add_hotkey("ctrl+alt+s", self.trigger_vision_from_hotkey)
        keyboard.add_hotkey("ctrl+alt+v", self.toggle_vad_from_hotkey)

    def toggle_audio_from_hotkey(self):
        if not self.recorder.recording:
            self.root.after(0, self.start_audio)
        else:
            self.root.after(0, self.stop_audio)
            self.root.after(500, self.process_transcription)

    def trigger_vision_from_hotkey(self):
        self.root.after(0, self.process_vision)

    def toggle_vad_from_hotkey(self):
        self.root.after(0, self.toggle_vad)

    def log(self, message):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, f"{message}\n\n")
        self.text_area.config(state=tk.DISABLED)
        self.text_area.see(tk.END)

    def clear_log(self):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.delete("1.0", tk.END)
        self.text_area.config(state=tk.DISABLED)

    def start_audio(self):
        self.recorder.start_recording()
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.log("Recording audio...")

    def stop_audio(self):
        self.recorder.stop_recording()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.log("Audio saved.")

    def process_transcription(self):
        self.transcribe_btn.config(state=tk.DISABLED)
        self.log("Sending audio to Whisper…")
        threading.Thread(target=self._run_transcription, daemon=True).start()

    def _run_transcription(self):
        result = self.ai.transcribe_audio("output.wav")
        self.root.after(0, self._transcription_done, result)

    def _transcription_done(self, result):
        self.log(f"Interviewer: {result}")
        self.transcribe_btn.config(state=tk.NORMAL)

    def toggle_vad(self):
        if self._vad_running:
            self._stop_vad()
        else:
            self._start_vad()

    def _start_vad(self):
        self._vad_running = True
        self.vad_btn.config(text="■ Stop VAD", bg="#e74c3c")
        self.vad_status.config(text="VAD: Listening…", fg="#2ecc71")
        self.log("VAD active — listening for speech automatically…")
        self.recorder.start_vad_recording(on_utterance_callback=self._on_vad_utterance)

    def _stop_vad(self):
        self.recorder.stop_vad_recording()
        self._vad_running = False
        self.vad_btn.config(text="▶ Start VAD", bg="#2ecc71")
        self.vad_status.config(text="VAD: Off", fg="grey")
        self.log("VAD stopped.")

    def _on_vad_utterance(self, wav_bytes: bytes):
        self.root.after(0, self.log, "🎙 Utterance detected — transcribing…")
        text = self.ai.transcribe_audio_bytes(wav_bytes)
        if text.strip():
            self.root.after(0, self.log, f"Interviewer: {text}")
        else:
            self.root.after(0, self.log, "(empty transcription — background noise?)")

    def take_screenshot(self):
        filename = self.capturer.capture()
        self.log("Screenshot captured.")
        return filename

    def process_vision(self):
        self.analyze_btn.config(state=tk.DISABLED)
        filename = self.take_screenshot()
        self.log("Sending screenshot to GPT-4o Vision…")
        threading.Thread(target=self._run_vision, args=(filename,), daemon=True).start()

    def _run_vision(self, filename):
        result = self.ai.analyze_screen(filename)
        self.root.after(0, self._vision_done, result)

    def _vision_done(self, result):
        self.log(f"AI Assistant: {result}")
        self.analyze_btn.config(state=tk.NORMAL)


def main():
    root = tk.Tk()
    app = CopilotApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()