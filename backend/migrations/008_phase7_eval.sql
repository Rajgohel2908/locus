-- migrations/008_phase7_eval.sql
-- Phase 7 Stage 1: Evaluation Suite Data Model
-- Applied by init_db() on startup; fully idempotent with IF NOT EXISTS.
-- Never UPDATE or DELETE rows of documents/records belonging to any existing version.

-- 1. eval_suites table
CREATE TABLE IF NOT EXISTS eval_suites (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NULL,
    source_ids INT[] NOT NULL,
    suite_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. eval_items table
CREATE TABLE IF NOT EXISTS eval_items (
    id SERIAL PRIMARY KEY,
    suite_id INT NOT NULL REFERENCES eval_suites(id) ON DELETE CASCADE,
    position INT NOT NULL DEFAULT 0,
    question TEXT NOT NULL,
    item_type TEXT NOT NULL CHECK (item_type IN ('answerable', 'unanswerable', 'structured')),
    expected_facts JSONB NOT NULL DEFAULT '[]',
    reference_answer TEXT NULL,
    expected_evidence JSONB NOT NULL DEFAULT '[]',
    expected_value JSONB NULL,
    expected_route TEXT NULL,
    origin TEXT NOT NULL DEFAULT 'agent_drafted' CHECK (origin IN ('hand', 'agent_drafted', 'generated')),
    reviewed BOOLEAN NOT NULL DEFAULT FALSE,
    tags JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_eval_items_suite_id ON eval_items(suite_id);

-- 3. eval_runs table
CREATE TABLE IF NOT EXISTS eval_runs (
    id SERIAL PRIMARY KEY,
    suite_id INT NOT NULL REFERENCES eval_suites(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    variant JSONB NOT NULL,
    config_hash TEXT NOT NULL,
    index_run_ids JSONB NOT NULL DEFAULT '{}',
    generate BOOLEAN NOT NULL DEFAULT FALSE,
    judge BOOLEAN NOT NULL DEFAULT FALSE,
    include_unreviewed BOOLEAN NOT NULL DEFAULT FALSE,
    llm JSONB NOT NULL DEFAULT '{}',
    judge_llm JSONB NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    progress JSONB NOT NULL DEFAULT '{}',
    error TEXT NULL,
    started_at TIMESTAMP NULL,
    finished_at TIMESTAMP NULL,
    seed INT NOT NULL DEFAULT 42,
    provenance JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_eval_runs_suite_id ON eval_runs(suite_id);

-- 4. eval_results table
CREATE TABLE IF NOT EXISTS eval_results (
    id SERIAL PRIMARY KEY,
    run_id INT NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
    item_id INT NOT NULL REFERENCES eval_items(id) ON DELETE CASCADE,
    query_id INT NULL REFERENCES queries(id) ON DELETE SET NULL,
    route TEXT NULL,
    strategy TEXT NULL,
    retrieved JSONB NOT NULL DEFAULT '[]',
    answer TEXT NULL,
    status TEXT NOT NULL,
    citations JSONB NOT NULL DEFAULT '[]',
    metrics JSONB NOT NULL DEFAULT '{}',
    latency_ms JSONB NOT NULL DEFAULT '{}',
    llm_calls INT NOT NULL DEFAULT 0,
    judge_calls INT NOT NULL DEFAULT 0,
    error TEXT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_run_item UNIQUE(run_id, item_id)
);

CREATE INDEX IF NOT EXISTS ix_eval_results_run_id ON eval_results(run_id);

