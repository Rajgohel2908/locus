-- migrations/007_phase6b.sql
-- Phase 6B: Rule-based strategy recommender and pipeline configs.
-- Applied by init_db() on startup; fully idempotent with IF NOT EXISTS.
-- Never UPDATE or DELETE rows of documents/records belonging to any existing version.

-- 1. recommendations table
CREATE TABLE IF NOT EXISTS recommendations (
    id SERIAL PRIMARY KEY,
    source_ids INT[] NOT NULL,
    goal TEXT NOT NULL,
    rules_version TEXT NOT NULL,
    data_profile JSONB NOT NULL,
    pipeline_spec JSONB NOT NULL,
    rules_fired JSONB NOT NULL,
    rules_not_fired JSONB NOT NULL,
    warnings JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed', 'approved', 'rejected', 'applied')),
    created_at TIMESTAMP DEFAULT NOW(),
    decided_at TIMESTAMP NULL
);

-- 2. pipeline_configs table
CREATE TABLE IF NOT EXISTS pipeline_configs (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('baseline', 'recommended')),
    source_ids INT[] NOT NULL,
    spec JSONB NOT NULL,
    spec_hash TEXT NOT NULL,
    recommendation_id INT NULL REFERENCES recommendations(id),
    index_runs JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. queries table: add pipeline_config_id column
ALTER TABLE queries ADD COLUMN IF NOT EXISTS pipeline_config_id INT NULL;

