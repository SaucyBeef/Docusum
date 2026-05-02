from database import queries


def store_document_chunks(document_id: int, chunks: list[str], embeddings: list[list[float]]) -> None:
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings must have the same length.")

    rows = []
    for index, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        rows.append((document_id, index, chunk_text, embedding))
    queries.insert_chunks(rows)


def retrieve_similar_chunks(
    query_embedding: list[float],
    user_id: int,
    document_id: int | None,
    limit: int,
) -> list[dict]:
    return queries.search_similar_chunks(
        query_embedding=query_embedding,
        user_id=user_id,
        document_id=document_id,
        limit=limit,
    )
