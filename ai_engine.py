import os
import io
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
                    file=audio_file,
                )
            return transcription.text
        except Exception as e:
            return f"API Error: {str(e)}"

    def transcribe_audio_bytes(self, wav_bytes: bytes) -> str:
        try:
            audio_file = io.BytesIO(wav_bytes)
            audio_file.name = "utterance.wav"
            transcription = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
            )
            return transcription.text
        except Exception as e:
            return f"API Error: {str(e)}"

    def analyze_screen(self, image_path: str) -> str:
        try:
            import base64
            if not os.path.exists(image_path):
                return "Error: Screenshot file not found."
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_data}"
                                },
                            },
                            {
                                "type": "text",
                                "text": (
                                    "You are an AI interview assistant. "
                                    "Analyse this screenshot and answer any "
                                    "question or coding problem visible. "
                                    "Be concise and direct."
                                ),
                            },
                        ],
                    }
                ],
                max_tokens=1024,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"API Error: {str(e)}"