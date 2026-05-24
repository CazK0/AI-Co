import sounddevice as sd
import numpy as np
from scipy.io import wavfile
import queue
import threading
import webrtcvad
import collections
import io
import wave


# VAD requires 16kHz, 16-bit mono audio
VAD_SAMPLE_RATE = 16000
# Frame duration in ms — 30ms is the max webrtcvad supports
VAD_FRAME_MS = 30
VAD_FRAME_SAMPLES = int(VAD_SAMPLE_RATE * VAD_FRAME_MS / 1000)  # 480 samples

# How many silent frames before we consider speech ended
SILENCE_THRESHOLD_FRAMES = 30  # ~900ms of silence triggers end of utterance


class AudioRecorder:
    """
    Records audio with two modes:

    1. Manual mode  — call start_recording() / stop_recording() as before.
    2. VAD mode     — call start_vad_recording(on_utterance_callback).
       The VAD continuously listens; whenever a complete utterance is
       detected (speech followed by silence) it fires on_utterance_callback
       with the WAV bytes so the caller can transcribe immediately.
    """

    def __init__(self, filename="output.wav", samplerate=44100):
        self.filename = filename
        self.samplerate = samplerate
        self.audio_queue = queue.Queue()
        self.recording = False
        self.stream = None

        # VAD state
        self._vad_active = False
        self._vad_thread = None
        self._on_utterance: callable = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_loopback_device(self):
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if "Loopback" in dev["name"] or "Stereo Mix" in dev["name"]:
                return i
        return sd.default.device[0]

    # ------------------------------------------------------------------
    # Manual recording (unchanged behaviour)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # VAD + live chunked transcription
    # ------------------------------------------------------------------

    def start_vad_recording(self, on_utterance_callback: callable):
        """
        Start continuous VAD listening.

        on_utterance_callback(wav_bytes: bytes) is called from a background
        thread each time a complete utterance is detected.  wav_bytes is a
        valid in-memory WAV file ready to send to Whisper.
        """
        if self._vad_active:
            return
        self._vad_active = True
        self._on_utterance = on_utterance_callback
        self._vad_thread = threading.Thread(
            target=self._vad_loop, daemon=True
        )
        self._vad_thread.start()

    def stop_vad_recording(self):
        self._vad_active = False

    def _vad_loop(self):
        vad = webrtcvad.Vad(2)  # aggressiveness 0-3; 2 is a good balance

        # Buffer of raw 16-bit PCM bytes for the current utterance
        voiced_frames: list[bytes] = []
        # Ring buffer for the "pre-roll" — keeps a short window of audio
        # before speech starts so we don't clip the first word
        ring_buffer = collections.deque(maxlen=15)  # ~450ms pre-roll
        in_speech = False
        silent_frame_count = 0

        # We record at VAD_SAMPLE_RATE directly for simplicity
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

                # Ensure we have exactly VAD_FRAME_SAMPLES samples
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
                        # Include pre-roll so first word isn't clipped
                        voiced_frames.extend(ring_buffer)
                        ring_buffer.clear()
                else:
                    voiced_frames.append(pcm_bytes)
                    if not is_speech:
                        silent_frame_count += 1
                        if silent_frame_count >= SILENCE_THRESHOLD_FRAMES:
                            # Utterance complete — fire callback
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
        """Convert a list of raw 16-bit PCM byte frames into WAV bytes."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(VAD_SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        return buf.getvalue()