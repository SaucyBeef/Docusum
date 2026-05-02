import hashlib
import math
import os
import random


EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1536"))
BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))


def embed_text(text: str) -> list[float]:
    return embed_chunks([text])[0]


def embed_chunks(chunks: list[str]) -> list[list[float]]:
    if not chunks:
        return []

    if _use_fake_embeddings():
        return [_fake_embedding(chunk) for chunk in chunks]

    client = _openai_client()
    vectors: list[list[float]] = []

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        vectors.extend([item.embedding for item in response.data])

    return vectors


def _use_fake_embeddings() -> bool:
    return os.getenv("RAG_USE_FAKE_EMBEDDINGS", "").lower() == "true" or not os.getenv("OPENAI_API_KEY")


def _openai_client():
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("openai package is required for embeddings.") from exc
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _fake_embedding(text: str) -> list[float]:
    seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
    rng = random.Random(seed)
    vec = [rng.uniform(-1.0, 1.0) for _ in range(EMBEDDING_DIM)]
    norm = math.sqrt(sum(value * value for value in vec))
    if norm == 0:
        return vec
    return [value / norm for value in vec]
