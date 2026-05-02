CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_history_user_id_created_at ON history(user_id, created_at DESC);

-- Cosine similarity index for pgvector search.
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_cosine
ON chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
