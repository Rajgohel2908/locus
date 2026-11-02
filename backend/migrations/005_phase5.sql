-- migrations/005_phase5.sql
-- Phase 5 Retrieval Upgrades & Explainability: document_overrides, query strategy & filters, candidate signals.
-- Applied by init_db() on startup; fully idempotent with IF NOT EXISTS.
-- Never UPDATE or DELETE rows of documents/records belonging to any existing version.

-- 1. document_overrides: allows user overrides for metadata without touching original document rows
CREATE TABLE IF NOT EXISTS document_overrides (
    id           SERIAL PRIMARY KEY,
    document_id  INT UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
    published_at TIMESTAMP NULL,
    title        TEXT NULL,
    set_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_document_overrides_document_id ON document_overrides(document_id);

-- 2. queries: add strategy and filters columns
ALTER TABLE queries ADD COLUMN IF NOT EXISTS strategy TEXT NOT NULL DEFAULT 'dense';
ALTER TABLE queries ADD COLUMN IF NOT EXISTS filters JSONB NOT NULL DEFAULT '{}';

-- 3. retrieval_results: add signals column for explainability
ALTER TABLE retrieval_results ADD COLUMN IF NOT EXISTS signals JSONB NOT NULL DEFAULT '{}';
