-- ============================================================
-- Migration: 001_initial_schema.sql
-- Description: MVP schema for NOVA (users, tasks, receipts, memory_vectors)
-- ============================================================

-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Helper function to handle auto-updating updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    full_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Trigger for users.updated_at
DROP TRIGGER IF EXISTS set_users_updated_at ON users;
CREATE TRIGGER set_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- 4. Tasks Table
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    payload JSONB DEFAULT '{}'::jsonb,
    result JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Trigger for tasks.updated_at
DROP TRIGGER IF EXISTS set_tasks_updated_at ON tasks;
CREATE TRIGGER set_tasks_updated_at
BEFORE UPDATE ON tasks
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- 5. Receipts Table
CREATE TABLE IF NOT EXISTS receipts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    action_type TEXT NOT NULL,
    tokens_used INTEGER NOT NULL DEFAULT 0,
    cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0.0,
    details JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Memory Vectors Table (pgvector)
-- embedding dimension matches all-MiniLM-L6-v2 (384-dim).
-- If you switch to an OpenAI text-embedding-ada-002 model, change to vector(1536).
CREATE TABLE IF NOT EXISTS memory_vectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    embedding vector(384),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Trigger for memory_vectors.updated_at
DROP TRIGGER IF EXISTS set_memory_vectors_updated_at ON memory_vectors;
CREATE TRIGGER set_memory_vectors_updated_at
BEFORE UPDATE ON memory_vectors
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_receipts_user_id ON receipts(user_id);
CREATE INDEX IF NOT EXISTS idx_receipts_task_id ON receipts(task_id);
CREATE INDEX IF NOT EXISTS idx_memory_vectors_user_id ON memory_vectors(user_id);

-- HNSW index for fast approximate nearest-neighbour search on 384-dim embeddings
CREATE INDEX IF NOT EXISTS idx_memory_vectors_embedding_hnsw
    ON memory_vectors USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- ============================================================
-- 7. match_memories RPC function (used by memory.py search_memory)
-- Returns top-k memories for a user ordered by cosine distance.
-- ============================================================
CREATE OR REPLACE FUNCTION match_memories(
    query_embedding  vector(384),
    match_threshold  float,
    match_count      int,
    p_user_id        uuid
)
RETURNS TABLE (
    id          uuid,
    content     text,
    metadata    jsonb,
    distance    float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        mv.id,
        mv.content,
        mv.metadata,
        (mv.embedding <=> query_embedding)::float AS distance
    FROM memory_vectors mv
    WHERE mv.user_id = p_user_id
      AND (mv.embedding <=> query_embedding) <= match_threshold
    ORDER BY mv.embedding <=> query_embedding
    LIMIT match_count;
$$;
