from flask import Blueprint, jsonify, request

from database import queries
from services.embedding import embed_text
from services.llm import generate_answer
from services.retrieval import retrieve_similar_chunks


query_bp = Blueprint("query", __name__, url_prefix="/query")


@query_bp.post("/")
def run_query() -> tuple:
    payload = request.get_json(silent=True) or {}

    user_id = payload.get("user_id")
    question = str(payload.get("question", "")).strip()
    top_k_raw = payload.get("top_k", 5)
    document_id = payload.get("document_id")

    if not isinstance(user_id, int):
        return jsonify({"error": "user_id is required and must be an integer."}), 400
    if not question:
        return jsonify({"error": "question is required."}), 400

    try:
        top_k = int(top_k_raw)
    except (TypeError, ValueError):
        return jsonify({"error": "top_k must be an integer."}), 400

    if top_k < 1 or top_k > 20:
        return jsonify({"error": "top_k must be between 1 and 20."}), 400

    if not queries.get_user_by_id(user_id):
        return jsonify({"error": "User not found."}), 404

    if document_id is not None:
        if not isinstance(document_id, int):
            return jsonify({"error": "document_id must be an integer when provided."}), 400
        if not queries.get_document_by_id(document_id=document_id, user_id=user_id):
            return jsonify({"error": "Document not found for this user."}), 404

    query_embedding = embed_text(question)
    retrieved_chunks = retrieve_similar_chunks(
        query_embedding=query_embedding,
        user_id=user_id,
        document_id=document_id,
        limit=top_k,
    )

    if not retrieved_chunks:
        answer = "I could not find relevant context in your uploaded documents."
        history = queries.create_history(
            user_id=user_id,
            question=question,
            answer=answer,
            document_id=document_id,
            contexts=[],
        )
        return jsonify({"answer": answer, "contexts": [], "history_id": history["id"]}), 200

    context_texts = [chunk["chunk_text"] for chunk in retrieved_chunks]
    answer = generate_answer(question=question, context_chunks=context_texts)
    history = queries.create_history(
        user_id=user_id,
        question=question,
        answer=answer,
        document_id=document_id,
        contexts=context_texts,
    )

    return jsonify(
        {
            "answer": answer,
            "history_id": history["id"],
            "contexts": [
                {
                    "chunk_id": row["id"],
                    "document_id": row["document_id"],
                    "chunk_index": row["chunk_index"],
                    "distance": float(row["distance"]),
                    "chunk_text": row["chunk_text"],
                }
                for row in retrieved_chunks
            ],
        }
    ), 200
