from flask import Blueprint, jsonify, request

from database import queries


history_bp = Blueprint("history", __name__, url_prefix="/history")


@history_bp.get("/<int:user_id>")
def get_history(user_id: int) -> tuple:
    if not queries.get_user_by_id(user_id):
        return jsonify({"error": "User not found."}), 404

    limit_raw = request.args.get("limit", "50")
    if not limit_raw.isdigit():
        return jsonify({"error": "limit must be an integer."}), 400
    limit = max(1, min(200, int(limit_raw)))

    records = queries.get_history(user_id=user_id, limit=limit)
    return jsonify(records), 200


@history_bp.delete("/<int:user_id>/<int:history_id>")
def delete_history_item(user_id: int, history_id: int) -> tuple:
    if not queries.get_user_by_id(user_id):
        return jsonify({"error": "User not found."}), 404

    deleted = queries.delete_history_item(user_id=user_id, history_id=history_id)
    if not deleted:
        return jsonify({"error": "History record not found."}), 404
    return jsonify({"deleted": True}), 200


@history_bp.delete("/<int:user_id>")
def clear_history(user_id: int) -> tuple:
    if not queries.get_user_by_id(user_id):
        return jsonify({"error": "User not found."}), 404

    deleted_count = queries.clear_history(user_id=user_id)
    return jsonify({"deleted_count": deleted_count}), 200
