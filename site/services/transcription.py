import requests
import os


WHISPER_ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"


WHISPER_MODEL = "whisper-1"


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


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
