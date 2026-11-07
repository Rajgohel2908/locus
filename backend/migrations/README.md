# backend/migrations/README.md

## How Migrations Work in Sift

Sift uses a **hybrid migration strategy**: SQLAlchemy ORM `create_all` for Phase 1 tables, then ordered SQL files for subsequent phases.

---

### Migration Files

| File | Phase | What it creates |
|---|---|---|
| *(ORM)* | Phase 1 | `files`, `quality_reports` — created by `Base.metadata.create_all()` in `db.py` |
| `002_phase2.sql` | Phase 2 | `sources`, `documents`, `records` |
| `003_phase3.sql` | Phase 3 | `source_versions`, `column_roles`, `cleaning_proposals` |
| `004_phase4.sql` | Phase 4 | `index_runs`, `chunks`, `queries`, `retrieval_results` |
| `005_phase5.sql` | Phase 5 | `document_overrides`, `queries.strategy`, `queries.filters`, `retrieval_results.signals` |
| `006_phase6.sql` | Phase 6 | `queries.route`, `queries.route_info`, `queries.answer_type` |
| `007_phase6b.sql` | Phase 6B | `recommendations`, `pipeline_configs`, `queries.pipeline_config_id` |
| `008_phase7_eval.sql` | Phase 7 Stage 1 | `eval_suites`, `eval_items`, `eval_runs`, `eval_results` |
| `009_phase7_doctor.sql` | Phase 7 Stage 2 | `doctor_reports`, `doctor_findings`, `pipeline_configs.kind` check extended |
| `010_phase7_1.sql` | Phase 7.1 | `doctor_findings.counterfactual`, evidence_level check ('observed','counterfactual','measured_effect','hypothesis') |

---

### How `init_db()` Applies Them

`db.py::init_db()` runs on every startup via the FastAPI `@app.on_event("startup")` hook:

```python
# Phase 1: ORM create_all (idempotent)
Base.metadata.create_all(bind=engine)

# Phase 2-6B: SQL files applied in order
for fname in ("002_phase2.sql", "003_phase3.sql", "004_phase4.sql", "005_phase5.sql", "006_phase6.sql", "007_phase6b.sql"):
    migration_path = Path(__file__).parent / "migrations" / fname
    ...
```

All SQL statements use `IF NOT EXISTS` / `ON CONFLICT DO NOTHING` so they are **fully idempotent** — safe to apply multiple times.

---

### Adding a New Migration (e.g., Phase 6)

1. Create `backend/migrations/006_phase6.sql` with all your `CREATE TABLE IF NOT EXISTS` or `ALTER TABLE` statements.
2. Add `"006_phase6.sql"` to the **ordered list** in `init_db()` in `db.py`:

   ```python
   for fname in ("002_phase2.sql", "003_phase3.sql", "004_phase4.sql", "005_phase5.sql", "006_phase6.sql"):
   ```

3. Add any new SQLAlchemy ORM models to `db.py` and call `Base.metadata.create_all()` will pick them up automatically.
4. Update this README table above with the new file.

> **Rule:** Never edit existing migration files once they have been applied to any environment.
> Always add a new numbered file instead.

---

### Resetting the Database (Development Only)

```bash
# Drop and recreate the sift database
psql -U postgres -c "DROP DATABASE IF EXISTS sift;"
psql -U postgres -c "CREATE DATABASE sift;"
psql -U postgres -d sift -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Restart the app — init_db() will re-apply all migrations
uvicorn main:app --reload
```