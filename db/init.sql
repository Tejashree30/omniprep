CREATE EXTENSION IF NOT EXISTS vector;
-- Optional native pgvector index for scale-up (app stores embeddings as JSON by default
-- and fuses BM25 + cosine in Python; migrate by copying embedding -> embedding_vec).
-- ALTER TABLE vector_chunks ADD COLUMN embedding_vec vector(256);
-- CREATE INDEX ON vector_chunks USING hnsw (embedding_vec vector_cosine_ops);
