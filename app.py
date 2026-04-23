import logging
from flask import Flask
from routes.voice_routes import voice_bp
from database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

init_db()

app = Flask(__name__)
app.register_blueprint(voice_bp)

@app.route("/", methods=["GET"])
def home():
    return {
        "status": "ok",
        "message": "Jarvis backend is running"
    }

if __name__ == "__main__":
    logging.getLogger(__name__).info("Starting Jarvis backend...")
    app.run(host="0.0.0.0", port=5000, debug=True)