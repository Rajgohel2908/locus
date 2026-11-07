-- migrations/009_phase7_doctor.sql
-- Phase 7 Stage 2: RAG Doctor v1 Data Model
-- Applied by init_db() on startup; fully idempotent with IF NOT EXISTS.
-- Never UPDATE or DELETE rows of documents/records belonging to any existing version.

-- 1. Extend pipeline_configs.kind check constraint to include 'doctor'
ALTER TABLE pipeline_configs DROP CONSTRAINT IF EXISTS pipeline_configs_kind_check;
ALTER TABLE pipeline_configs ADD CONSTRAINT pipeline_configs_kind_check CHECK (kind IN ('baseline', 'recommended', 'doctor'));

-- 2. doctor_reports table
CREATE TABLE IF NOT EXISTS doctor_reports (
    id SERIAL PRIMARY KEY,
    run_ids INT[] NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    summary JSONB NOT NULL DEFAULT '{}'
);

-- 3. doctor_findings table
CREATE TABLE IF NOT EXISTS doctor_findings (
    id SERIAL PRIMARY KEY,
    report_id INT NOT NULL REFERENCES doctor_reports(id) ON DELETE CASCADE,
    rule_id TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'warning', 'info')),
    title TEXT NOT NULL,
    diagnosis TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}',
    evidence_level TEXT NOT NULL CHECK (evidence_level IN ('measured', 'hypothesis')),
    proposed_patch JSONB NOT NULL DEFAULT '{}',
    expected_effect TEXT NOT NULL,
    cost_note TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed', 'approved', 'rejected', 'applied', 'verified_improved', 'verified_no_change', 'verified_regressed')),
    applied_config_id INT NULL REFERENCES pipeline_configs(id),
    verification_run_id INT NULL REFERENCES eval_runs(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_doctor_findings_report_id ON doctor_findings(report_id);
CREATE INDEX IF NOT EXISTS ix_doctor_findings_status ON doctor_findings(status);
