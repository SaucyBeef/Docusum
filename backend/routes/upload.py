from flask import Blueprint, jsonify, request

from database import queries
from services.chunking import chunk_text
from services.embedding import embed_chunks
from services.parsing import extract_text
from services.retrieval import store_document_chunks


upload_bp = Blueprint("upload", __name__, url_prefix="/upload")


@upload_bp.post("/")
def upload_document() -> tuple:
    user_id_raw = request.form.get("user_id", "").strip()
    if not user_id_raw.isdigit():
        return jsonify({"error": "user_id must be a valid integer."}), 400
    user_id = int(user_id_raw)

    user = queries.get_user_by_id(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "file is required."}), 400

    file_bytes = file.read()
    if not file_bytes:
        return jsonify({"error": "Uploaded file is empty."}), 400

    try:
        parsed_text = extract_text(file.filename, file.content_type, file_bytes)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    chunks = chunk_text(parsed_text)
    if not chunks:
        return jsonify({"error": "Could not produce chunks from file."}), 400

    embeddings = embed_chunks(chunks)

    document = queries.create_document(
        user_id=user_id,
        file_name=file.filename,
        file_type=file.content_type or "application/octet-stream",
        text_content=parsed_text,
    )
    store_document_chunks(document["id"], chunks, embeddings)

    return jsonify(
        {
            "document_id": document["id"],
            "file_name": document["file_name"],
            "chunk_count": len(chunks),
            "created_at": document["created_at"],
        }
    ), 201


@upload_bp.get("/documents/<int:user_id>")
def list_documents(user_id: int) -> tuple:
    if not queries.get_user_by_id(user_id):
        return jsonify({"error": "User not found."}), 404
    return jsonify(queries.list_user_documents(user_id)), 200
