import os
import requests
from pydub import AudioSegment
from dotenv import load_dotenv

load_dotenv()


WHISPER_MODEL = "whisper-1"



def transcribe_audio(audio_data: bytes) -> str:

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }

    files = {
        "file": ("audio.wav", audio_data, "audio/wav"),
        "model": (None, WHISPER_MODEL),
    }

    response = requests.post(WHISPER_ENDPOINT, headers=headers, files=files)

    if response.status_code == 200:
        return response.json().get("text", "")
    else:
        raise Exception(f"Ошибка при транскрипции: {response.status_code} - {response.text}")

if __name__ == "__main__":
    input_file_path = "temp_audio.webm"
    audio = AudioSegment.from_file(input_file_path, format="webm")
    print(transcribe_audio_with_prepare_data(audio))