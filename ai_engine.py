import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class AIEngine:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def transcribe_audio(self, file_path="output.wav"):
        try:
            if not os.path.exists(file_path):
                return "Error: Audio file not found."

            with open(file_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            return transcription.text
        except Exception as e:
            return f"API Error: {str(e)}"