import os

INPUT_FILE = "audio_in/input.wav"
OUTPUT_FILE = "audio_out/response.mp3"

os.makedirs("audio_in", exist_ok=True)
os.makedirs("audio_out", exist_ok=True)
os.makedirs("data", exist_ok=True)