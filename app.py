import logging
import os
from dotenv import load_dotenv

# Load environment variables before any other imports
load_dotenv()

from flask import Flask, jsonify
from flask_cors import CORS
from models import db
from api import bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)
    db_uri = os.getenv("DATABASE_URL")
    if db_uri and db_uri.startswith("postgres://"):
        db_uri = db_uri.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri or "sqlite:///spendwise.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if config:
        app.config.update(config)

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    db.init_app(app)

    with app.app_context():
        db.create_all()

    app.register_blueprint(bp)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"ok": False, "error": "not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return jsonify({"ok": False, "error": "method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(e):
        logging.getLogger(__name__).exception("Unhandled error")
        return jsonify({"ok": False, "error": "internal server error"}), 500

    return app


# Create WSGI application for servers (Gunicorn, etc.) to import
application = create_app()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "False").lower() in ("1", "true")
    port = int(os.getenv("PORT", 5000))
    application.run(debug=debug, port=port)
