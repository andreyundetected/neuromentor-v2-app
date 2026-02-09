import os
import requests
from pydub import AudioSegment
from dotenv import load_dotenv

load_dotenv()








if __name__ == "__main__":
    input_file_path = "temp_audio.webm"
    audio = AudioSegment.from_file(input_file_path, format="webm")
    print(transcribe_audio_with_prepare_data(audio))