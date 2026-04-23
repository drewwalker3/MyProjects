from gtts import gTTS

def text_to_speech(text: str, output_path: str) -> None:
    tts = gTTS(text=text, lang="en")
    tts.save(output_path)