import tkinter as tk
import ctypes
from audio import AudioRecorder


class CopilotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Copilot UI")
        self.root.geometry("500x600")
        self.root.attributes("-topmost", True)

        self.recorder = AudioRecorder()

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

        self.stop_btn = tk.Button(self.btn_frame, text="Stop Recording", command=self.stop_audio, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

    def log(self, message):
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, f"{message}\n")
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


def main():
    root = tk.Tk()
    app = CopilotApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()