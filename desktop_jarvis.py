import os
import time
import tempfile
import threading
import subprocess

import numpy as np
import requests
import sounddevice as sd
from openwakeword.model import Model
from scipy.io.wavfile import write


BACKEND_VOICE_URL = "http://127.0.0.1:5000/voice"
BACKEND_AUDIO_URL = "http://127.0.0.1:5000/audio"
BACKEND_STATUS_URL = "http://127.0.0.1:5000/assistant-status/update"

CUSTOM_WAKE_MODEL_PATH = "/Users/andrewwalker/Desktop/jarvis-vr/desktop-client/wake_models/hey_rex.onnx"

print("MODEL EXISTS:", os.path.exists(CUSTOM_WAKE_MODEL_PATH))
print("MODEL PATH:", CUSTOM_WAKE_MODEL_PATH)


def find_input_device_index(preferred_name: str) -> int:
    devices = sd.query_devices()

    for i, device in enumerate(devices):
        name = device["name"].lower()
        max_input = device["max_input_channels"]
        if preferred_name.lower() in name and max_input > 0:
            return i

    raise RuntimeError(f"Could not find input device containing: {preferred_name}")


class DesktopJarvisApp:
    def __init__(self):
        self.is_speaking = False
        self.playback_process = None
        self.is_listening_for_wake = False
        self.is_processing_command = False
        self.wake_model = None
        self.wake_thread = None
        self.followup_active_until = 0

        self.initialize_wake_model()
        self.start_wake_listener()

    def push_status(self, mode=None, transcript=None, reply=None):
        try:
            requests.post(
                BACKEND_STATUS_URL,
                json={
                    "mode": mode,
                    "transcript": transcript,
                    "reply": reply,
                },
                timeout=5,
            )
        except Exception as e:
            print("Status push error:", e)

    def initialize_wake_model(self):
        if not os.path.exists(CUSTOM_WAKE_MODEL_PATH):
            raise FileNotFoundError(
                f"Custom wake model not found: {CUSTOM_WAKE_MODEL_PATH}"
            )

        import openwakeword
        base_dir = os.path.join(os.path.dirname(openwakeword.__file__), "resources", "models")

        melspec_path = os.path.join(base_dir, "melspectrogram.onnx")
        embedding_path = os.path.join(base_dir, "embedding_model.onnx")

        print("Using melspec model:", melspec_path, os.path.exists(melspec_path))
        print("Using embedding model:", embedding_path, os.path.exists(embedding_path))

        self.wake_model = Model(
            wakeword_models=[CUSTOM_WAKE_MODEL_PATH],
            melspec_model_path=melspec_path,
            embedding_model_path=embedding_path,
        )
        print("Loaded custom wake model:", CUSTOM_WAKE_MODEL_PATH)

    def start_wake_listener(self):
        if self.wake_thread and self.wake_thread.is_alive():
            return

        self.is_listening_for_wake = True
        self.wake_thread = threading.Thread(target=self.wake_listen_loop, daemon=True)
        self.wake_thread.start()

        print("Listening for wake word...")
        self.push_status(mode="ready")

    def wake_listen_loop(self):
        input_device_index = find_input_device_index("MacBook Air Microphone")
        device_info = sd.query_devices(input_device_index)

        print("Wake listener using input device index:", input_device_index)
        print("Wake listener device name:", device_info["name"])

        sample_rate = 16000
        chunk_size = 1280

        # Your logs showed the hey_rex model usually sits around ~0.0008
        # with occasional higher peaks, so keep this low for testing.
        min_wake_amplitude = 200
        wake_threshold = 0.0023

        try:
            with sd.InputStream(
                samplerate=sample_rate,
                blocksize=chunk_size,
                device=input_device_index,
                channels=1,
                dtype="int16"
            ) as stream:
                print("Wake input stream opened")

                while self.is_listening_for_wake:
                    if self.is_processing_command or self.is_speaking:
                        time.sleep(0.1)
                        continue

                    try:
                        audio, _ = stream.read(chunk_size)
                        audio_chunk = audio.flatten()

                        max_amp = int(np.abs(audio_chunk).max())
                        prediction = self.wake_model.predict(audio_chunk)

                        rex_score = 0.0
                        for key, value in prediction.items():
                            score = float(value)
                            if "rex" in key.lower():
                                rex_score = score

                        if rex_score > 0.001:
                            print(f"wake max amplitude: {max_amp} | hey_rex: {rex_score:.6f}")

                        if max_amp > min_wake_amplitude and rex_score > wake_threshold:
                            print("WAKE WORD DETECTED:", rex_score)
                            self.handle_wake_detected()
                            break

                    except Exception as e:
                        print("Wake listener error:", e)
                        time.sleep(0.25)

        finally:
            self.wake_thread = None

    def followup_active(self):
        return time.time() < self.followup_active_until

    def handle_wake_detected(self):
        self.is_listening_for_wake = False
        self.push_status(mode="listening")
        self.followup_active_until = time.time() + 60
        print("Wake word detected. Listening...")
        time.sleep(0.2)
        threading.Thread(target=self.handle_talk, daemon=True).start()

    def record_audio_to_wav(self, output_path: str):
        self.push_status(mode="listening")
        print("Listening for command...")

        input_device_index = find_input_device_index("MacBook Air Microphone")
        print("Using input device index:", input_device_index)

        command_sample_rate = 16000
        command_chunk_size = 1024
        silence_threshold = 300
        silence_duration_limit = 1.2
        max_command_seconds = 10
        no_speech_timeout = 3.0

        collected_chunks = []
        silence_start = None
        start_time = time.time()
        speech_started = False

        with sd.InputStream(
            samplerate=command_sample_rate,
            blocksize=command_chunk_size,
            device=input_device_index,
            channels=1,
            dtype="int16"
        ) as stream:
            print("Command input stream opened")

            while True:
                audio, _ = stream.read(command_chunk_size)
                audio_chunk = audio.flatten()
                max_amp = int(np.abs(audio_chunk).max())

                collected_chunks.append(audio_chunk)

                now = time.time()

                if max_amp > silence_threshold:
                    speech_started = True
                    silence_start = None
                else:
                    if speech_started:
                        if silence_start is None:
                            silence_start = now
                        elif now - silence_start >= silence_duration_limit:
                            print("Silence detected, ending command capture")
                            break
                    else:
                        if now - start_time >= no_speech_timeout:
                            print("No speech detected after wake word")
                            break

                if now - start_time >= max_command_seconds:
                    print("Max command duration reached")
                    break

        if not collected_chunks:
            raise RuntimeError("No audio captured")

        full_audio = np.concatenate(collected_chunks).astype(np.int16)
        print("Final command max amplitude:", int(np.abs(full_audio).max()))
        write(output_path, command_sample_rate, full_audio)

    def send_audio_to_backend(self, wav_path: str):
        self.push_status(mode="thinking")
        print("Sending audio to backend...")

        with open(wav_path, "rb") as audio_file:
            files = {
                "file": ("input.wav", audio_file, "audio/wav")
            }
            response = requests.post(BACKEND_VOICE_URL, files=files, timeout=120)

        response.raise_for_status()
        return response.json()

    def download_and_play_response_audio(self):
        self.push_status(mode="speaking")
        print("Downloading and playing response audio...")

        response = requests.get(BACKEND_AUDIO_URL, timeout=120)
        response.raise_for_status()

        print("Downloaded audio bytes:", len(response.content))
        if len(response.content) < 1000:
            raise RuntimeError("Downloaded audio file is too small to be valid")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_audio.write(response.content)
            temp_audio_path = temp_audio.name

        self.is_speaking = True

        try:
            self.playback_process = subprocess.Popen(["afplay", temp_audio_path])
            self.playback_process.wait()
        finally:
            self.is_speaking = False
            self.playback_process = None

            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)

    def handle_talk(self):
        if self.is_processing_command:
            return

        self.is_processing_command = True
        temp_wav_path = None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_wav:
                temp_wav_path = temp_wav.name

            self.is_listening_for_wake = False
            self.record_audio_to_wav(temp_wav_path)

            result = self.send_audio_to_backend(temp_wav_path)
            print("BACKEND RESULT:", result)

            transcript = result.get("transcript", "")
            reply = result.get("reply", "")
            audio_url = result.get("audio_url", "")

            if not transcript.strip():
                print("Empty transcript detected. Ignoring silent input.")
                self.push_status(mode="ready", transcript="", reply="")
                return
            
            if transcript.strip():
                self.followup_active_until = time.time() + 60

            print("TRANSCRIPT:", transcript)
            print("REPLY:", repr(reply))
            print("AUDIO URL:", repr(audio_url))

            self.push_status(
                mode="speaking" if audio_url else "ready",
                transcript=transcript,
                reply=reply
            )

            if audio_url:
                self.download_and_play_response_audio()
            else:
                print("No audio URL returned; staying text-only.")

        except Exception as e:
            print("Error:", str(e))
            self.push_status(mode="ready", reply=f"Error: {str(e)}")

        finally:
            if temp_wav_path and os.path.exists(temp_wav_path):
                os.remove(temp_wav_path)

            self.is_processing_command = False
            self.push_status(mode="ready")
            print("Ready")
            time.sleep(0.3)

            if self.followup_active():
                print("Follow-up window active. Listening for next command...")
                threading.Thread(target=self.handle_talk, daemon=True).start()
            else:
                self.start_wake_listener()

    def run_forever(self):
        print("Rex headless listener is running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping Rex...")


def main():
    app = DesktopJarvisApp()
    app.run_forever()


if __name__ == "__main__":
    main()