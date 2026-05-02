import json
from pathlib import Path

import psycopg

from database.db import get_db_connection


SQL_DIR = Path(__file__).parent


def initialize_database() -> None:
    schema_sql = (SQL_DIR / "schema.sql").read_text(encoding="utf-8")
    indexes_sql = (SQL_DIR / "indexes.sql").read_text(encoding="utf-8")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(schema_sql)
                cur.execute(indexes_sql)
            conn.commit()
    except psycopg.errors.FeatureNotSupported as exc:
        message = str(exc).lower()
        if 'extension "vector" is not available' in message:
            raise RuntimeError(
                "pgvector extension is not installed in this PostgreSQL instance. "
                "Install pgvector, then run: CREATE EXTENSION IF NOT EXISTS vector;"
            ) from exc
        raise


def create_user(email: str, password_hash: str, name: str | None) -> dict:
    sql = """
        INSERT INTO users (email, password_hash, name)
        VALUES (%s, %s, %s)
        RETURNING id, email, name, created_at;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (email, password_hash, name))
            row = cur.fetchone()
        conn.commit()
    return row


def get_user_by_email(email: str) -> dict | None:
    sql = """
        SELECT id, email, password_hash, name, created_at
        FROM users
        WHERE email = %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (email,))
            return cur.fetchone()


def get_user_by_id(user_id: int) -> dict | None:
    sql = """
        SELECT id, email, name, created_at
        FROM users
        WHERE id = %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return cur.fetchone()


def create_document(user_id: int, file_name: str, file_type: str, text_content: str) -> dict:
    sql = """
        INSERT INTO documents (user_id, file_name, file_type, text_content)
        VALUES (%s, %s, %s, %s)
        RETURNING id, user_id, file_name, file_type, created_at;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, file_name, file_type, text_content))
            row = cur.fetchone()
        conn.commit()
    return row


def get_document_by_id(document_id: int, user_id: int | None = None) -> dict | None:
    if user_id is None:
        sql = """
            SELECT id, user_id, file_name, file_type, created_at
            FROM documents
            WHERE id = %s;
        """
        params = (document_id,)
    else:
        sql = """
            SELECT id, user_id, file_name, file_type, created_at
            FROM documents
            WHERE id = %s AND user_id = %s;
        """
        params = (document_id, user_id)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def list_user_documents(user_id: int) -> list[dict]:
    sql = """
        SELECT id, user_id, file_name, file_type, created_at
        FROM documents
        WHERE user_id = %s
        ORDER BY created_at DESC;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return cur.fetchall()


def insert_chunks(chunk_rows: list[tuple[int, int, str, list[float]]]) -> None:
    if not chunk_rows:
        return

    sql = """
        INSERT INTO chunks (document_id, chunk_index, chunk_text, embedding)
        VALUES (%s, %s, %s, %s::vector);
    """
    rows = [
        (document_id, chunk_index, chunk_text, _vector_literal(embedding))
        for document_id, chunk_index, chunk_text, embedding in chunk_rows
    ]

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, rows)
        conn.commit()


def search_similar_chunks(
    query_embedding: list[float],
    user_id: int,
    document_id: int | None,
    limit: int,
) -> list[dict]:
    vector_literal = _vector_literal(query_embedding)
    if document_id is None:
        sql = """
            SELECT
                c.id,
                c.document_id,
                c.chunk_index,
                c.chunk_text,
                (c.embedding <=> %s::vector) AS distance
            FROM chunks c
            INNER JOIN documents d ON d.id = c.document_id
            WHERE d.user_id = %s
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s;
        """
        execute_params = (vector_literal, user_id, vector_literal, limit)
    else:
        sql = """
            SELECT
                c.id,
                c.document_id,
                c.chunk_index,
                c.chunk_text,
                (c.embedding <=> %s::vector) AS distance
            FROM chunks c
            INNER JOIN documents d ON d.id = c.document_id
            WHERE d.user_id = %s
              AND c.document_id = %s
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s;
        """
        execute_params = (vector_literal, user_id, document_id, vector_literal, limit)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, execute_params)
            return cur.fetchall()


def create_history(
    user_id: int,
    question: str,
    answer: str,
    document_id: int | None,
    contexts: list[str],
) -> dict:
    sql = """
        INSERT INTO history (user_id, document_id, question, answer, contexts_json)
        VALUES (%s, %s, %s, %s, %s::jsonb)
        RETURNING id, user_id, document_id, question, answer, contexts_json, created_at;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, document_id, question, answer, json.dumps(contexts)))
            row = cur.fetchone()
        conn.commit()
    return row


def get_history(user_id: int, limit: int) -> list[dict]:
    sql = """
        SELECT id, user_id, document_id, question, answer, contexts_json, created_at
        FROM history
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id, limit))
            return cur.fetchall()


def delete_history_item(user_id: int, history_id: int) -> bool:
    sql = """
        DELETE FROM history
        WHERE id = %s AND user_id = %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (history_id, user_id))
            deleted = cur.rowcount > 0
        conn.commit()
    return deleted


def clear_history(user_id: int) -> int:
    sql = """
        DELETE FROM history
        WHERE user_id = %s;
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            deleted_count = cur.rowcount
        conn.commit()
    return deleted_count


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"
