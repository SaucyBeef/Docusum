import hashlib
import hmac
import os
import secrets

from flask import Blueprint, jsonify, request

from database import queries


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

PBKDF2_ITERATIONS = int(os.getenv("PASSWORD_HASH_ITERATIONS", "600000"))


def _json_body() -> dict:
    return request.get_json(silent=True) or {}


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        _, iterations, salt, digest = stored_hash.split("$", maxsplit=3)
        computed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(computed, digest)
    except ValueError:
        return False


def _validate_credentials(payload: dict) -> tuple[str | None, str | None]:
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))

    if not email or "@" not in email:
        return None, "A valid email is required."
    if len(password) < 8:
        return None, "Password must be at least 8 characters."
    return email, None


@auth_bp.post("/register")
def register() -> tuple:
    payload = _json_body()
    email, error = _validate_credentials(payload)
    if error:
        return jsonify({"error": error}), 400

    if queries.get_user_by_email(email):
        return jsonify({"error": "Email is already registered."}), 409

    user = queries.create_user(
        email=email,
        password_hash=_hash_password(str(payload["password"])),
        name=str(payload.get("name", "")).strip() or None,
    )
    return jsonify(
        {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "created_at": user["created_at"],
        }
    ), 201


@auth_bp.post("/login")
def login() -> tuple:
    payload = _json_body()
    email, error = _validate_credentials(payload)
    if error:
        return jsonify({"error": error}), 400

    user = queries.get_user_by_email(email)
    if not user or not _verify_password(str(payload["password"]), user["password_hash"]):
        return jsonify({"error": "Invalid email or password."}), 401

    return jsonify(
        {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "created_at": user["created_at"],
        }
    ), 200
