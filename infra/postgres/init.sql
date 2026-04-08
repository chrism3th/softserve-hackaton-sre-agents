-- Initial schema bootstrapping.
-- Keep this small: use Alembic migrations for anything non-trivial.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Example placeholder table. Replace with real domain tables as needed.
CREATE TABLE IF NOT EXISTS agent_invocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    input TEXT NOT NULL,
    output TEXT,
    tokens_used INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invocations_created_at
    ON agent_invocations (created_at DESC);
