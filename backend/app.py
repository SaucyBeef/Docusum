import os

from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from database.queries import initialize_database
from routes.auth import auth_bp
from routes.history import history_bp
from routes.query import query_bp
from routes.upload import upload_bp


load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__)

    origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",")]
    CORS(app, origins=origins, supports_credentials=True)

    try:
        initialize_database()
    except Exception as exc:
        raise RuntimeError(
            "Database initialization failed. Verify DATABASE_URL or DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD in .env."
        ) from exc

    @app.get("/health")
    def health() -> tuple:
        return jsonify({"status": "ok"}), 200

    app.register_blueprint(auth_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(query_bp)
    app.register_blueprint(history_bp)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "5000")), debug=False)
