import requests
import os

url = "http://127.0.0.1:5000/voice"

with open("test.wav", "rb") as f:
    files = {"file": f}
    response = requests.post(url, files=files)

print("Status code:", response.status_code)
print("Response text:")
print(response.text)

if response.status_code == 200:
    data = response.json()
    audio_url = data.get("audio_url", "")

    if audio_url:
        audio_response = requests.get("http://127.0.0.1:5000" + audio_url)
        with open("downloaded_response.mp3", "wb") as out:
            out.write(audio_response.content)
        print("Saved audio to downloaded_response.mp3")
        os.system("open downloaded_response.mp3")
    else:
        print("No audio was generated.")