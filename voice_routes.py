from flask import Blueprint, request, jsonify, send_file
import os
import logging


from config import INPUT_FILE, OUTPUT_FILE
from services.stt_service import transcribe_audio
from services.tts_service import text_to_speech
from services.router_service import interpret_command
from handlers.system.dispatcher import dispatch
from services.history_service import save_command_history

logger = logging.getLogger(__name__)

voice_bp = Blueprint("voice", __name__)

@voice_bp.route("/voice", methods=["POST"])
def voice():
    logger.info("Received /voice request")

    if "file" not in request.files:
        logger.warning("No audio file received in /voice request")
        return jsonify({"error": "No audio file received"}), 400

    audio_file = request.files["file"]

    try:
        audio_file.save(INPUT_FILE)
        logger.info("Saved input audio to %s", INPUT_FILE)
    except Exception:
        logger.exception("Failed to save uploaded audio")
        return jsonify({"error": "Failed to save uploaded audio"}), 500

    try:
        user_text = transcribe_audio(INPUT_FILE)
        logger.info("Transcribed user text: %s", user_text)
    except Exception:
        logger.exception("Speech transcription failed")
        return jsonify({"error": "Speech transcription failed"}), 500

    try:
        command = interpret_command(user_text)
        logger.info("Interpreted command: %s", command)
    except Exception:
        logger.exception("Command interpretation failed")
        return jsonify({"error": "Command interpretation failed"}), 500

    try:
        jarvis_reply = dispatch(command)
        logger.info("Jarvis reply: %s", jarvis_reply)
    except Exception:
        logger.exception("Command dispatch failed")
        return jsonify({"error": "Command dispatch failed"}), 500

    try:
        save_command_history(user_text, command, jarvis_reply, source="voice")
    except Exception:
        logger.exception("Failed to save command history")

    if jarvis_reply is None:
        logger.info("No spoken reply generated because command returned None")
        return jsonify({
            "transcript": user_text,
            "command": command,
            "reply": "",
            "audio_url": ""
        })

    audio_url = ""

    try:
        text_to_speech(jarvis_reply, OUTPUT_FILE)
        logger.info("Generated speech output at %s", OUTPUT_FILE)

        if os.path.exists(OUTPUT_FILE):
            audio_url = "/audio"
        else:
            logger.warning("TTS ran but output file was not found: %s", OUTPUT_FILE)
    except Exception:
        logger.exception("Text-to-speech generation failed")

    return jsonify({
        "transcript": user_text,
        "command": command,
        "reply": jarvis_reply,
        "audio_url": audio_url
    })

@voice_bp.route("/audio", methods=["GET"])
def audio():
    logger.info("Received /audio request")

    if not os.path.exists(OUTPUT_FILE):
        logger.error("Missing audio file: %s", OUTPUT_FILE)
        return jsonify({"error": f"Missing audio file: {OUTPUT_FILE}"}), 500
    
    return send_file(OUTPUT_FILE, mimetype="audio/mpeg")

@voice_bp.route("/chat", methods=["POST"])
def chat():
    logger.info("Received /chat request")

    data = request.get_json()

    if not data or "text" not in data:
        logger.warning("No text provided in /chat request")
        return jsonify({"error": "No text provided"}), 400

    user_text = data["text"].strip()
    logger.info("Chat user text: %s", user_text)

    try:
        command = interpret_command(user_text)
        logger.info("Interpreted chat command: %s", command)
    except Exception:
        logger.exception("Chat command interpretation failed")
        return jsonify({"error": "Command interpretation failed"}), 500

    try:
        jarvis_reply = dispatch(command)
        logger.info("Chat Jarvis reply: %s", jarvis_reply)
    except Exception:
        logger.exception("Chat command dispatch failed")
        return jsonify({"error": "Command dispatch failed"}), 500

    try:
        save_command_history(user_text, command, jarvis_reply, source="chat")
    except Exception:
        logger.exception("Failed to save chat command history")

    return jsonify({
        "transcript": user_text,
        "command": command,
        "reply": jarvis_reply or ""
    })