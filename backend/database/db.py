import os
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row


def _database_url() -> str:
    configured = os.getenv("DATABASE_URL", "").strip()
    if configured:
        if configured.startswith("jdbc:postgresql://"):
            configured = configured.replace("jdbc:postgresql://", "postgresql://", 1)
        return configured

    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "docusum")
    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"


@contextmanager
def get_db_connection():
    conn = psycopg.connect(_database_url(), row_factory=dict_row, autocommit=False)
    try:
        yield conn
    finally:
        conn.close()
