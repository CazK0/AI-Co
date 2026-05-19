import sounddevice as sd
import numpy as np
from scipy.io import wavfile
import queue
import threading


class AudioRecorder:
    def __init__(self, filename="output.wav", samplerate=44100):
        self.filename = filename
        self.samplerate = samplerate
        self.audio_queue = queue.Queue()
        self.recording = False
        self.stream = None

    def _callback(self, indata, frames, time, status):
        self.audio_queue.put(indata.copy())

    def start_recording(self):
        self.recording = True
        wasapi_loopback = sd.AsioSettings() if hasattr(sd, 'AsioSettings') else None

        devices = sd.query_devices()
        default_loopback = None
        for i, dev in enumerate(devices):
            if "Loopback" in dev["name"] or "Stereo Mix" in dev["name"]:
                default_loopback = i
                break

        device_index = default_loopback if default_loopback is not None else sd.default.device[0]

        self.stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=1,
            device=device_index,
            callback=self._callback
        )
        self.stream.start()

        threading.Thread(target=self._write_file, daemon=True).start()

    def _write_file(self):
        with wavfile.write(self.filename, self.samplerate, np.zeros((0, 1), dtype=np.float32)) as f:
            pass

        all_data = []
        while self.recording or not self.audio_queue.empty():
            try:
                data = self.audio_queue.get(timeout=0.5)
                all_data.append(data)
            except queue.Empty:
                continue

        if all_data:
            final_audio = np.concatenate(all_data, axis=0)
            wavfile.write(self.filename, self.samplerate, final_audio)

    def stop_recording(self):
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()