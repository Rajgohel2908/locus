-- migrations/010_phase7_1.sql
-- Phase 7.1: Evidence Levels, Counterfactuals, and Diagnostic Enhancements
-- Applied by init_db() on startup; fully idempotent.
-- Never UPDATE or DELETE rows of documents/records belonging to any existing version.

-- 1. Migrate any existing 'measured' values to 'measured_effect'
UPDATE doctor_findings SET evidence_level = 'measured_effect' WHERE evidence_level = 'measured';

-- 2. Update check constraint on doctor_findings.evidence_level
ALTER TABLE doctor_findings DROP CONSTRAINT IF EXISTS doctor_findings_evidence_level_check;
ALTER TABLE doctor_findings ADD CONSTRAINT doctor_findings_evidence_level_check 
    CHECK (evidence_level IN ('observed', 'counterfactual', 'measured_effect', 'hypothesis'));

-- 3. Add counterfactual JSONB column to doctor_findings
ALTER TABLE doctor_findings ADD COLUMN IF NOT EXISTS counterfactual JSONB DEFAULT '{}'::jsonb;

