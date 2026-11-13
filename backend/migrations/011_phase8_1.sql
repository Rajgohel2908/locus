-- migrations/011_phase8_1.sql
-- Phase 8.1: Dev/Holdout Split and Diagnostic Finding Status Extension
-- Applied by init_db() on startup; fully idempotent.
-- Never UPDATE or DELETE rows of documents/records belonging to any existing version.

-- 1. Add split column to eval_items
ALTER TABLE eval_items ADD COLUMN IF NOT EXISTS split TEXT NULL;

-- 2. Add / replace check constraint on eval_items.split ('dev' | 'holdout' | NULL)
ALTER TABLE eval_items DROP CONSTRAINT IF EXISTS eval_items_split_check;
ALTER TABLE eval_items ADD CONSTRAINT eval_items_split_check 
    CHECK (split IS NULL OR split IN ('dev', 'holdout'));

-- 3. Extend doctor_findings.status check constraint to include 'verified_inconclusive_small_n'
ALTER TABLE doctor_findings DROP CONSTRAINT IF EXISTS doctor_findings_status_check;
ALTER TABLE doctor_findings ADD CONSTRAINT doctor_findings_status_check 
    CHECK (status IN (
        'proposed', 
        'approved', 
        'rejected', 
        'applied', 
        'verified_improved', 
        'verified_no_change', 
        'verified_regressed', 
        'verified_inconclusive_small_n'
    ));

