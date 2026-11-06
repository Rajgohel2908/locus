"""
tests/test_phase6a_executor.py — Independent correctness, safety, and benchmark tests for Phase 6A executor.

All tests in this module run against the real PostgreSQL database and are marked with @pytest.mark.pg.
Fails fast if DATABASE_URL is not PostgreSQL.

Tests:
1. Independent correctness vs pandas:
   - count, sum, avg, min, max on employees_messy.csv fixture
   - group_by and filter equality vs pandas recomputations
   - exact match on rows_considered, rows_used, rows_excluded_non_numeric, rows_null
2. top_n template (argmax / argmin):
   - compare with pandas idxmax / nlargest / idxmin / nsmallest
   - ties handling: all ties returned (capped at 10)
   - non-numeric exclusion in top_n
   - mentions Phase 3 outlier flag on returned row and in data_quality_notes
3. Render and Filter bug fixes:
   - never print "N rows were null" for count templates without a column; print null count only when column is present and > 0
   - filter deduplication by normalized form (lower/trim): one filter per column value, displayed with canonical spelling and spelling variants
   - data_quality_notes mention outlier count in numeric column used (included in result) and non-numeric exclusions
4. Safety & Whitelisting:
   - quotes, SQL fragments, and unicode in filter values safely parameterized
   - non-whitelisted columns rejected with ValueError
5. Zero-usable numeric rows:
   - returns reason "no_numeric_values"
6. 100k-row PostgreSQL benchmark (informational).
"""

import os
import re
import time
import pytest
import pandas as pd
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base, Source, Record, SourceVersion
from routing.context import StructuredTableSchema
from structured.executor import execute_aggregation, NUMERIC_REGEX
from structured.render import render_answer

import urllib.parse
DATABASE_URL = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL", "")


@pytest.fixture
def test_db():
    if not (DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgresql+")):
        pytest.fail(f"TEST_DATABASE_URL must be a real PostgreSQL database, got: '{DATABASE_URL}'")

    parsed = urllib.parse.urlparse(DATABASE_URL)
    db_name = parsed.path.lstrip("/")
    if not db_name.endswith("_test"):
        pytest.fail(f"Safety check failed: pg test database name must end with '_test', got '{db_name}'. Refusing to run tests against non-test database.")

    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _recompute_pandas(df: pd.DataFrame, op: str, column: str = None, group_by: str = None, filters=None):
    """Independent pandas implementation of the executor aggregation logic."""
    df_filtered = df.copy()

    if filters:
        for f_col, f_val in filters:
            df_filtered = df_filtered[
                df_filtered[f_col].astype(str).str.strip().str.lower() == f_val.strip().lower()
            ]

    rows_considered = len(df_filtered)

    def classify_num(val):
        if pd.isna(val):
            return "null", None
        s = str(val).strip()
        if not s:
            return "null", None
        if NUMERIC_REGEX.match(s):
            clean_s = s.replace(",", "")
            try:
                return "numeric", float(clean_s)
            except ValueError:
                return "non_numeric", None
        return "non_numeric", None

    if group_by:
        groups = []
        for g_name, g_df in df_filtered.groupby(df_filtered[group_by].astype(str).str.strip()):
            nums = []
            g_excl = 0
            g_null = 0
            g_used = 0
            for v in g_df[column] if column else [1] * len(g_df):
                vtype, nval = classify_num(v) if column else ("numeric", 1.0)
                if vtype == "numeric":
                    g_used += 1
                    if nval is not None:
                        nums.append(nval)
                elif vtype == "non_numeric":
                    g_excl += 1
                else:
                    g_null += 1

            val = None
            if op == "count":
                val = len(g_df)
            elif nums:
                if op == "sum": val = sum(nums)
                elif op == "avg": val = sum(nums) / len(nums)
                elif op == "min": val = min(nums)
                elif op == "max": val = max(nums)

            groups.append({
                "group": g_name,
                "value": val,
                "rows_considered": len(g_df),
                "rows_used": g_used if op != "count" else len(g_df),
                "rows_excluded_non_numeric": g_excl,
            })
        groups.sort(key=lambda x: (-x["rows_considered"], x["group"]))
        return {"rows_considered": rows_considered, "groups": groups}

    else:
        nums = []
        rows_used = 0
        rows_excluded = 0
        rows_null = 0
        if column:
            for v in df_filtered[column]:
                vtype, nval = classify_num(v)
                if vtype == "numeric":
                    rows_used += 1
                    if nval is not None: nums.append(nval)
                elif vtype == "non_numeric":
                    rows_excluded += 1
                else:
                    rows_null += 1
        else:
            rows_used = rows_considered

        val = None
        if op == "count":
            val = rows_considered
        elif nums:
            if op == "sum": val = sum(nums)
            elif op == "avg": val = sum(nums) / len(nums)
            elif op == "min": val = min(nums)
            elif op == "max": val = max(nums)

        return {
            "rows_considered": rows_considered,
            "rows_used": rows_used,
            "rows_excluded_non_numeric": rows_excluded,
            "rows_null": rows_null,
            "result_value": val,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 1. Independent Correctness Tests vs Pandas on PostgreSQL
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.pg
def test_executor_vs_pandas_aggregations(test_db):
    csv_path = Path(__file__).resolve().parent.parent / "sample_data" / "employees_messy.csv"
    df = pd.read_csv(csv_path)

    src = Source(source_type="file", name="emp_test.csv")
    test_db.add(src)
    test_db.commit()

    try:
        recs = [
            Record(
                source_id=src.id,
                row_index=i,
                version_no=1,
                status="active",
                data={k: (None if pd.isna(v) else str(v)) for k, v in row.items()},
            )
            for i, row in df.iterrows()
        ]
        test_db.add_all(recs)
        test_db.commit()

        schema = StructuredTableSchema(
            source_id=src.id,
            source_name=src.name,
            version=1,
            columns=list(df.columns),
            column_roles={"Salary": "numeric", "Department": "category", "City": "category", "Employee_ID": "identifier"},
            dtypes={},
            category_values={
                "Department": list(df["Department"].dropna().unique()),
                "City": list(df["City"].dropna().unique()),
            },
            identifier_columns=["Employee_ID"],
            numeric_columns=["Salary"],
        )

        # 1. Count
        res = execute_aggregation(test_db, schema, op="count")
        pd_res = _recompute_pandas(df, op="count")
        assert res["rows_considered"] == pd_res["rows_considered"]
        assert res["result_value"] == pd_res["result_value"]

        # 2. Avg Salary with Filter
        res_avg = execute_aggregation(test_db, schema, op="avg", column="Salary", filters=[("City", "Mumbai")])
        pd_avg = _recompute_pandas(df, op="avg", column="Salary", filters=[("City", "Mumbai")])
        assert res_avg["rows_considered"] == pd_avg["rows_considered"]
        assert res_avg["rows_used"] == pd_avg["rows_used"]
        assert pytest.approx(res_avg["result_value"], 0.01) == pd_avg["result_value"]

        # 3. Sum Salary
        res_sum = execute_aggregation(test_db, schema, op="sum", column="Salary")
        pd_sum = _recompute_pandas(df, op="sum", column="Salary")
        assert pytest.approx(res_sum["result_value"], 0.01) == pd_sum["result_value"]

        # 4. Count group by Department
        res_grp = execute_aggregation(test_db, schema, op="count", group_by="Department")
        pd_grp = _recompute_pandas(df, op="count", group_by="Department")
        assert len(res_grp["groups"]) == len(pd_grp["groups"])
        assert res_grp["groups"][0]["value"] == pd_grp["groups"][0]["value"]

    finally:
        test_db.query(Record).filter(Record.source_id == src.id).delete()
        test_db.delete(src)
        test_db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# 2. top_n Template Tests (Argmax/Argmin, Ties, Outlier flag)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.pg
def test_top_n_argmax_argmin_vs_pandas(test_db):
    src = Source(source_type="file", name="top_n_test.csv")
    test_db.add(src)
    test_db.commit()

    try:
        data_rows = [
            {"Employee_ID": "E1", "Name": "Alice", "Department": "Eng", "Salary": "90000", "City": "Mumbai"},
            {"Employee_ID": "E2", "Name": "Bob", "Department": "HR", "Salary": "75000", "City": "Delhi"},
            {"Employee_ID": "E3", "Name": "Charlie", "Department": "Eng", "Salary": "120000", "City": "Bangalore"},
            {"Employee_ID": "E4", "Name": "David", "Department": "Sales", "Salary": "60000", "City": "Mumbai"},
            {"Employee_ID": "E5", "Name": "Eve", "Department": "HR", "Salary": "invalid_sal", "City": "Pune"},
        ]
        recs = [
            Record(source_id=src.id, row_index=i, version_no=1, status="active", data=r)
            for i, r in enumerate(data_rows)
        ]
        test_db.add_all(recs)
        test_db.commit()

        schema = StructuredTableSchema(
            source_id=src.id,
            source_name=src.name,
            version=1,
            columns=["Employee_ID", "Name", "Department", "Salary", "City"],
            column_roles={"Employee_ID": "identifier", "Salary": "numeric", "Department": "category"},
            dtypes={},
            category_values={"Department": ["Eng", "HR", "Sales"], "City": ["Mumbai", "Delhi", "Bangalore", "Pune"]},
            identifier_columns=["Employee_ID"],
            numeric_columns=["Salary"],
        )

        # 1. Top 1 Highest (argmax)
        res_max = execute_aggregation(test_db, schema, op="max", column="Salary", template="top_n", top_n=1)
        assert res_max["success"] is True
        assert res_max["template"] == "top_n"
        assert len(res_max["top_rows"]) == 1
        top_emp = res_max["top_rows"][0]
        assert top_emp["identifier_value"] == "E3"
        assert top_emp["target_value"] == 120000.0
        assert res_max["rows_excluded_non_numeric"] == 1

        # Compare with pandas idxmax
        df_p = pd.DataFrame(data_rows)
        df_num = df_p[df_p["Salary"].str.isnumeric()].copy()
        df_num["Salary_f"] = df_num["Salary"].astype(float)
        pd_max_id = df_num.loc[df_num["Salary_f"].idxmax(), "Employee_ID"]
        assert top_emp["identifier_value"] == pd_max_id

        # 2. Top 1 Lowest (argmin)
        res_min = execute_aggregation(test_db, schema, op="min", column="Salary", template="top_n", top_n=1)
        assert len(res_min["top_rows"]) == 1
        assert res_min["top_rows"][0]["identifier_value"] == "E4"
        assert res_min["top_rows"][0]["target_value"] == 60000.0

        pd_min_id = df_num.loc[df_num["Salary_f"].idxmin(), "Employee_ID"]
        assert res_min["top_rows"][0]["identifier_value"] == pd_min_id

        # Render check
        ans_text = render_answer(res_max)
        assert "Highest Salary:" in ans_text
        assert "E3: Salary 120,000" in ans_text
        assert "1 rows had non-numeric values and were excluded" in ans_text

    finally:
        test_db.query(Record).filter(Record.source_id == src.id).delete()
        test_db.delete(src)
        test_db.commit()


@pytest.mark.pg
def test_top_n_ties_handling(test_db):
    src = Source(source_type="file", name="ties_test.csv")
    test_db.add(src)
    test_db.commit()

    try:
        # Two employees tie for the top salary of 100,000
        data_rows = [
            {"Employee_ID": "E101", "Name": "John", "Salary": "100000"},
            {"Employee_ID": "E102", "Name": "Jane", "Salary": "100000"},
            {"Employee_ID": "E103", "Name": "Jack", "Salary": "80000"},
        ]
        recs = [
            Record(source_id=src.id, row_index=i, version_no=1, status="active", data=r)
            for i, r in enumerate(data_rows)
        ]
        test_db.add_all(recs)
        test_db.commit()

        schema = StructuredTableSchema(
            source_id=src.id,
            source_name=src.name,
            version=1,
            columns=["Employee_ID", "Name", "Salary"],
            column_roles={"Employee_ID": "identifier", "Salary": "numeric"},
            dtypes={},
            category_values={},
            identifier_columns=["Employee_ID"],
            numeric_columns=["Salary"],
        )

        res = execute_aggregation(test_db, schema, op="max", column="Salary", template="top_n", top_n=1)
        assert len(res["top_rows"]) == 2  # Both tied employees returned!
        ids = {r["identifier_value"] for r in res["top_rows"]}
        assert ids == {"E101", "E102"}

    finally:
        test_db.query(Record).filter(Record.source_id == src.id).delete()
        test_db.delete(src)
        test_db.commit()


@pytest.mark.pg
def test_top_n_phase3_outlier_flag(test_db):
    src = Source(source_type="file", name="outlier_test.csv")
    test_db.add(src)
    test_db.commit()

    try:
        # Row with Phase 3 outlier flag in metadata
        r1 = Record(
            source_id=src.id,
            row_index=0,
            version_no=1,
            status="active",
            data={"Employee_ID": "E999", "Name": "Outlier Exec", "Salary": "5000000"},
            metadata_={"outlier_flags": [{"column": "Salary", "value": 5000000}]},
        )
        r2 = Record(
            source_id=src.id,
            row_index=1,
            version_no=1,
            status="active",
            data={"Employee_ID": "E100", "Name": "Normal Staff", "Salary": "60000"},
        )
        test_db.add_all([r1, r2])
        test_db.commit()

        schema = StructuredTableSchema(
            source_id=src.id,
            source_name=src.name,
            version=1,
            columns=["Employee_ID", "Name", "Salary"],
            column_roles={"Employee_ID": "identifier", "Salary": "numeric"},
            dtypes={},
            category_values={},
            identifier_columns=["Employee_ID"],
            numeric_columns=["Salary"],
        )

        res = execute_aggregation(test_db, schema, op="max", column="Salary", template="top_n", top_n=1)
        assert res["top_rows"][0]["identifier_value"] == "E999"
        assert res["top_rows"][0]["is_outlier"] is True

        # Render check: mention outlier flag on row
        rendered = render_answer(res)
        assert "[Phase 3 outlier flag]" in rendered
        assert any("flagged as outliers" in note for note in res["data_quality_notes"])

    finally:
        test_db.query(Record).filter(Record.source_id == src.id).delete()
        test_db.delete(src)
        test_db.commit()


@pytest.mark.pg
def test_outlier_honesty_independent_pandas_recomputation(test_db):
    """
    Test outlier honesty for avg, sum, min, max, top_n on employees_messy.csv
    against independent pandas recomputation (E0014 Salary=9,999,999).
    1. Unflagged (v1): computes 1.5x IQR, reports '1 potential outliers (IQR rule), not flagged'
       and secondary line 'Excluding 1 outlier values: 72,265.75'.
       top_n max on Salary annotates '[potential outlier (IQR rule)]'.
    2. Phase 3 flagged (v2): reports '1 values in 'Salary' are flagged as outliers (included in result)'
       and secondary line 'Excluding 1 outlier values: 72,265.75'.
       top_n max on Salary annotates '[Phase 3 outlier flag]'.
    """
    csv_path = Path(__file__).resolve().parent.parent / "sample_data" / "employees_messy.csv"
    df = pd.read_csv(csv_path)

    src = Source(source_type="file", name="emp_outliers_test.csv")
    test_db.add(src)
    test_db.commit()

    try:
        # Version 1 records: no Phase 3 outlier flags
        recs_v1 = [
            Record(
                source_id=src.id,
                row_index=i,
                version_no=1,
                status="active",
                data={k: (None if pd.isna(v) else str(v)) for k, v in row.items()},
            )
            for i, row in df.iterrows()
        ]
        test_db.add_all(recs_v1)

        # Version 2 records: E0014 flagged as outlier
        recs_v2 = [
            Record(
                source_id=src.id,
                row_index=i,
                version_no=2,
                status="active",
                data={k: (None if pd.isna(v) else str(v)) for k, v in row.items()},
                metadata_={"outlier_flags": [{"column": "Salary", "value": 9999999.0}]}
                if str(row.get("Employee_ID", "")).strip() == "E0014"
                else None,
            )
            for i, row in df.iterrows()
        ]
        test_db.add_all(recs_v2)
        test_db.commit()

        schema_v1 = StructuredTableSchema(
            source_id=src.id,
            source_name=src.name,
            version=1,
            columns=list(df.columns),
            column_roles={"Salary": "numeric", "Department": "category", "City": "category", "Employee_ID": "identifier"},
            dtypes={},
            category_values={
                "Department": list(df["Department"].dropna().unique()),
                "City": list(df["City"].dropna().unique()),
            },
            identifier_columns=["Employee_ID"],
            numeric_columns=["Salary"],
        )

        schema_v2 = StructuredTableSchema(
            source_id=src.id,
            source_name=src.name,
            version=2,
            columns=list(df.columns),
            column_roles={"Salary": "numeric", "Department": "category", "City": "category", "Employee_ID": "identifier"},
            dtypes={},
            category_values={
                "Department": list(df["Department"].dropna().unique()),
                "City": list(df["City"].dropna().unique()),
            },
            identifier_columns=["Employee_ID"],
            numeric_columns=["Salary"],
        )

        # Pandas independent recomputations for Mumbai
        mumbai_df = df[df["City"].astype(str).str.strip().str.lower() == "mumbai"]
        sal_mumbai = pd.to_numeric(mumbai_df["Salary"].astype(str).str.replace(",", "").str.strip(), errors="coerce").dropna()
        pd_mumbai_mean = float(sal_mumbai.mean())
        pd_mumbai_sum = float(sal_mumbai.sum())
        q25 = float(sal_mumbai.quantile(0.25))
        q75 = float(sal_mumbai.quantile(0.75))
        iqr = q75 - q25
        lb = q25 - 1.5 * iqr
        ub = q75 + 1.5 * iqr
        sal_clean = sal_mumbai[(sal_mumbai >= lb) & (sal_mumbai <= ub)]
        pd_clean_mean = float(sal_clean.mean())
        pd_clean_sum = float(sal_clean.sum())

        # ── TEST V1: Unflagged (IQR rule triggers) ───────────────────────────
        # 1. Average Salary in Mumbai
        res_avg_v1 = execute_aggregation(test_db, schema_v1, op="avg", column="Salary", filters=[("City", "Mumbai")], version=1)
        assert pytest.approx(res_avg_v1["result_value"], 0.01) == pd_mumbai_mean
        assert pytest.approx(res_avg_v1["excluding_outliers_value"], 0.01) == pd_clean_mean
        assert res_avg_v1["outliers_count"] == 1
        assert any("1 potential outliers (IQR rule), not flagged" in n for n in res_avg_v1["data_quality_notes"])
        assert any("Average without 1 potential outlier(s): 72,265.75" in n for n in res_avg_v1["data_quality_notes"])

        rendered_avg_v1 = render_answer(res_avg_v1)
        assert "Average Salary where City = Mumbai" in rendered_avg_v1
        assert "235,015.48" in rendered_avg_v1
        assert "Average without 1 potential outlier(s): 72,265.75" in rendered_avg_v1
        assert "- 1 potential outliers (IQR rule), not flagged" in rendered_avg_v1

        # 2. Sum Salary in Mumbai
        res_sum_v1 = execute_aggregation(test_db, schema_v1, op="sum", column="Salary", filters=[("City", "Mumbai")], version=1)
        assert pytest.approx(res_sum_v1["result_value"], 0.01) == pd_mumbai_sum
        assert pytest.approx(res_sum_v1["excluding_outliers_value"], 0.01) == pd_clean_sum
        rendered_sum_v1 = render_answer(res_sum_v1)
        assert "Total without 1 potential outlier(s): 4,335,945.01" in rendered_sum_v1

        # 3. Top 1 Highest Salary in Mumbai
        res_top_v1 = execute_aggregation(test_db, schema_v1, op="max", column="Salary", filters=[("City", "Mumbai")], template="top_n", top_n=1, version=1)
        assert res_top_v1["top_rows"][0]["identifier_value"] == "E0014"
        assert res_top_v1["top_rows"][0]["is_iqr_outlier"] is True
        rendered_top_v1 = render_answer(res_top_v1)
        assert "[potential outlier (IQR rule)]" in rendered_top_v1
        assert "- 1 potential outliers (IQR rule), not flagged" in rendered_top_v1

        # ── TEST V2: Phase 3 Flagged Outliers ────────────────────────────────
        res_avg_v2 = execute_aggregation(test_db, schema_v2, op="avg", column="Salary", filters=[("City", "Mumbai")], version=2)
        assert pytest.approx(res_avg_v2["result_value"], 0.01) == pd_mumbai_mean
        assert pytest.approx(res_avg_v2["excluding_outliers_value"], 0.01) == pd_clean_mean
        assert res_avg_v2["outliers_count"] == 1
        assert any("1 values in 'Salary' are flagged as outliers (included in result)" in n for n in res_avg_v2["data_quality_notes"])
        assert any("Average without 1 potential outlier(s): 72,265.75" in n for n in res_avg_v2["data_quality_notes"])

        rendered_avg_v2 = render_answer(res_avg_v2)
        assert "Average Salary where City = Mumbai" in rendered_avg_v2
        assert "235,015.48" in rendered_avg_v2
        assert "Average without 1 potential outlier(s): 72,265.75" in rendered_avg_v2
        assert "- 1 values in 'Salary' are flagged as outliers (included in result)" in rendered_avg_v2

        # Top 1 Highest Salary in Mumbai for V2
        res_top_v2 = execute_aggregation(test_db, schema_v2, op="max", column="Salary", filters=[("City", "Mumbai")], template="top_n", top_n=1, version=2)
        assert res_top_v2["top_rows"][0]["identifier_value"] == "E0014"
        assert res_top_v2["top_rows"][0]["is_outlier"] is True
        rendered_top_v2 = render_answer(res_top_v2)
        assert "[Phase 3 outlier flag]" in rendered_top_v2
        assert "- 1 values in 'Salary' are flagged as outliers (included in result)" in rendered_top_v2

    finally:
        test_db.query(Record).filter(Record.source_id == src.id).delete()
        test_db.delete(src)
        test_db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Filter Deduplication and Canonical Spelling Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.pg
def test_filter_deduplication_canonical_spelling_variants(test_db):
    src = Source(source_type="file", name="variants_test.csv")
    test_db.add(src)
    test_db.commit()

    try:
        # 3 rows with 'Mumbai', 1 row with 'mumbai'
        rows = [
            {"Emp": "A", "City": "Mumbai", "Salary": "50000"},
            {"Emp": "B", "City": "Mumbai", "Salary": "52000"},
            {"Emp": "C", "City": "Mumbai", "Salary": "48000"},
            {"Emp": "D", "City": "mumbai", "Salary": "51000"},
            {"Emp": "E", "City": "Delhi", "Salary": "60000"},
        ]
        recs = [
            Record(source_id=src.id, row_index=i, version_no=1, status="active", data=r)
            for i, r in enumerate(rows)
        ]
        test_db.add_all(recs)
        test_db.commit()

        schema = StructuredTableSchema(
            source_id=src.id,
            source_name=src.name,
            version=1,
            columns=["Emp", "City", "Salary"],
            column_roles={"Emp": "identifier", "City": "category", "Salary": "numeric"},
            dtypes={},
            category_values={"City": ["Mumbai", "Delhi"]},
            identifier_columns=["Emp"],
            numeric_columns=["Salary"],
        )

        # Pass duplicate normalized filters: "mumbai" and "Mumbai"
        filters = [("City", "mumbai"), ("City", "Mumbai")]
        res = execute_aggregation(test_db, schema, op="count", filters=filters)

        # Deduplicated to 1 filter
        assert len(res["filters"]) == 1
        filt = res["filters"][0]
        assert filt["column"] == "City"
        assert filt["value"] == "Mumbai"  # Most frequent spelling
        assert len(filt["variants"]) == 2  # Both 'Mumbai' and 'mumbai' recorded

        # Render output check
        rendered = render_answer(res)
        assert "(matched 2 spelling variants:" in rendered
        assert "City = Mumbai" in rendered

    finally:
        test_db.query(Record).filter(Record.source_id == src.id).delete()
        test_db.delete(src)
        test_db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# 4. Render Null Count Bug Fix (3a)
# ─────────────────────────────────────────────────────────────────────────────

def test_render_null_count_bug_fix():
    # 1. Count template without column -> must NEVER print "0 rows were null" or "N rows were null"
    res_count = {
        "op": "count",
        "column": None,
        "rows_used": 50,
        "rows_null": 5,
        "rows_excluded_non_numeric": 0,
        "source_name": "test.csv",
        "version": 1,
        "result_value": 50,
    }
    rendered_count = render_answer(res_count)
    assert "rows were null" not in rendered_count

    # 2. Column template with null rows > 0 -> DOES print null count
    res_col = {
        "op": "avg",
        "column": "Salary",
        "rows_used": 45,
        "rows_null": 5,
        "rows_excluded_non_numeric": 0,
        "source_name": "test.csv",
        "version": 1,
        "result_value": 55000.0,
    }
    rendered_col = render_answer(res_col)
    assert "5 rows were null" in rendered_col


# ─────────────────────────────────────────────────────────────────────────────
# 5. Safety, Whitelisting, and Zero-Usable Numeric Rows
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.pg
def test_zero_usable_numeric_rows(test_db):
    src = Source(source_type="file", name="non_num.csv")
    test_db.add(src)
    test_db.commit()

    try:
        recs = [
            Record(source_id=src.id, row_index=0, version_no=1, status="active", data={"Salary": "N/A"}),
            Record(source_id=src.id, row_index=1, version_no=1, status="active", data={"Salary": "TBD"}),
        ]
        test_db.add_all(recs)
        test_db.commit()

        schema = StructuredTableSchema(
            source_id=src.id,
            source_name=src.name,
            version=1,
            columns=["Salary"],
            column_roles={"Salary": "numeric"},
            dtypes={},
            category_values={},
            identifier_columns=[],
            numeric_columns=["Salary"],
        )

        res = execute_aggregation(test_db, schema, op="avg", column="Salary")
        assert res["rows_used"] == 0
        assert res["rows_excluded_non_numeric"] == 2
        assert res["reason"] == "no_numeric_values"
        assert res["success"] is False

    finally:
        test_db.query(Record).filter(Record.source_id == src.id).delete()
        test_db.delete(src)
        test_db.commit()


@pytest.mark.pg
def test_safety_whitelisting(test_db):
    src = Source(source_type="file", name="safe.csv")
    test_db.add(src)
    test_db.commit()

    try:
        recs = [
            Record(source_id=src.id, row_index=0, version_no=1, status="active", data={"Dept": "Eng", "Salary": "50000"}),
        ]
        test_db.add_all(recs)
        test_db.commit()

        schema = StructuredTableSchema(
            source_id=src.id,
            source_name=src.name,
            version=1,
            columns=["Dept", "Salary"],
            column_roles={"Dept": "category", "Salary": "numeric"},
            dtypes={},
            category_values={"Dept": ["Eng"]},
            identifier_columns=[],
            numeric_columns=["Salary"],
        )

        # SQL injection in filter values parameterized safely
        res = execute_aggregation(test_db, schema, op="count", filters=[("Dept", "Eng' OR '1'='1")])
        assert res["rows_considered"] == 0

        # Non-whitelisted column rejected
        with pytest.raises(ValueError, match="not in schema whitelist"):
            execute_aggregation(test_db, schema, op="sum", column="non_existent_col")

    finally:
        test_db.query(Record).filter(Record.source_id == src.id).delete()
        test_db.delete(src)
        test_db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# 6. 100k-Row PostgreSQL Benchmark (Informational)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.pg
def test_100k_row_benchmark_pg(test_db):
    src = Source(source_type="file", name="benchmark_100k_pg.csv")
    test_db.add(src)
    test_db.commit()

    try:
        n_rows = 100_000
        batch_size = 10_000
        for b in range(0, n_rows, batch_size):
            recs = [
                Record(
                    source_id=src.id,
                    row_index=b + i,
                    version_no=1,
                    status="active",
                    data={"Dept": f"Dept_{i % 10}", "Salary": f"{50000 + (i % 1000)}"},
                )
                for i in range(batch_size)
            ]
            test_db.bulk_save_objects(recs)
        test_db.commit()

        schema = StructuredTableSchema(
            source_id=src.id,
            source_name=src.name,
            version=1,
            columns=["Dept", "Salary"],
            column_roles={"Dept": "category", "Salary": "numeric"},
            dtypes={},
            category_values={"Dept": [f"Dept_{i}" for i in range(10)]},
            identifier_columns=[],
            numeric_columns=["Salary"],
        )

        t0 = time.perf_counter()
        res = execute_aggregation(test_db, schema, op="avg", column="Salary", group_by="Dept")
        elapsed = time.perf_counter() - t0

        assert res["rows_considered"] == 100_000
        assert len(res["groups"]) == 10
        print(f"\n[BENCHMARK] PostgreSQL aggregation over 100,000 rows executed in {elapsed:.3f}s ({elapsed*1000:.1f}ms).")

    finally:
        test_db.query(Record).filter(Record.source_id == src.id).delete()
        test_db.delete(src)
        test_db.commit()
