-- migrations/006_phase6.sql
-- Phase 6A: Rule-based routing and structured deterministic aggregation path.
-- Applied by init_db() on startup; fully idempotent with IF NOT EXISTS.
-- Never UPDATE or DELETE rows of documents/records belonging to any existing version.

-- 1. queries: add route, route_info, and answer_type columns
ALTER TABLE queries ADD COLUMN IF NOT EXISTS route TEXT NULL;
ALTER TABLE queries ADD COLUMN IF NOT EXISTS route_info JSONB NOT NULL DEFAULT '{}';
ALTER TABLE queries ADD COLUMN IF NOT EXISTS answer_type TEXT NOT NULL DEFAULT 'generated';
