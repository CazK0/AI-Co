import sounddevice as sd
import numpy as np
from scipy.io import wavfile
import queue
import threading
import webrtcvad
import collections
import io
import wave

VAD_SAMPLE_RATE = 16000
VAD_FRAME_MS = 30
VAD_FRAME_SAMPLES = int(VAD_SAMPLE_RATE * VAD_FRAME_MS / 1000)
SILENCE_THRESHOLD_FRAMES = 30


class AudioRecorder:
    def __init__(self, filename="output.wav", samplerate=44100):
        self.filename = filename
        self.samplerate = samplerate
        self.audio_queue = queue.Queue()
        self.recording = False
        self.stream = None
        self._vad_active = False
        self._vad_thread = None
        self._on_utterance: callable = None

    def _find_loopback_device(self):
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if "Loopback" in dev["name"] or "Stereo Mix" in dev["name"]:
                return i
        return sd.default.device[0]

    def _manual_callback(self, indata, frames, time, status):
        self.audio_queue.put(indata.copy())

    def start_recording(self):
        self.recording = True
        device_index = self._find_loopback_device()
        self.stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=1,
            device=device_index,
            callback=self._manual_callback,
        )
        self.stream.start()
        threading.Thread(target=self._write_file, daemon=True).start()

    def _write_file(self):
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

    def start_vad_recording(self, on_utterance_callback: callable):
        if self._vad_active:
            return
        self._vad_active = True
        self._on_utterance = on_utterance_callback
        self._vad_thread = threading.Thread(target=self._vad_loop, daemon=True)
        self._vad_thread.start()

    def stop_vad_recording(self):
        self._vad_active = False

    def _vad_loop(self):
        vad = webrtcvad.Vad(2)
        voiced_frames: list[bytes] = []
        ring_buffer = collections.deque(maxlen=15)
        in_speech = False
        silent_frame_count = 0
        raw_queue: queue.Queue = queue.Queue()

        def vad_callback(indata, frames, time_info, status):
            raw_queue.put(indata.copy())

        device_index = self._find_loopback_device()
        stream = sd.InputStream(
            samplerate=VAD_SAMPLE_RATE,
            channels=1,
            dtype="int16",
            device=device_index,
            blocksize=VAD_FRAME_SAMPLES,
            callback=vad_callback,
        )
        stream.start()

        try:
            while self._vad_active:
                try:
                    frame = raw_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                if len(frame) != VAD_FRAME_SAMPLES:
                    continue

                pcm_bytes = frame.tobytes()

                try:
                    is_speech = vad.is_speech(pcm_bytes, VAD_SAMPLE_RATE)
                except Exception:
                    is_speech = False

                if not in_speech:
                    ring_buffer.append(pcm_bytes)
                    if is_speech:
                        in_speech = True
                        silent_frame_count = 0
                        voiced_frames.extend(ring_buffer)
                        ring_buffer.clear()
                else:
                    voiced_frames.append(pcm_bytes)
                    if not is_speech:
                        silent_frame_count += 1
                        if silent_frame_count >= SILENCE_THRESHOLD_FRAMES:
                            wav_bytes = self._frames_to_wav(voiced_frames)
                            threading.Thread(
                                target=self._on_utterance,
                                args=(wav_bytes,),
                                daemon=True,
                            ).start()
                            voiced_frames.clear()
                            ring_buffer.clear()
                            in_speech = False
                            silent_frame_count = 0
                    else:
                        silent_frame_count = 0
        finally:
            stream.stop()
            stream.close()

    @staticmethod
    def _frames_to_wav(frames: list[bytes]) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(VAD_SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        return buf.getvalue()