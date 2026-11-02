r"""
structured/executor.py — Deterministic structured aggregation engine.

Fixed aggregation templates:
- count, sum, avg, min, max
- top_n (argmax/argmin with ties)
- Optional group_by (one category column, capped at 50 groups)
- Optional equality filters (AND, case/space-insensitive, deduplicated by normalized spelling)
- Single structured source, latest or requested version, status = 'active' only
- Whitelist validation on all column names before execution
- Bound parameters for EVERYTHING including JSONB keys (data ->> :col)
- Shared numeric parsing: ^\s*-?[0-9][0-9,]*(\.[0-9]+)?\s*$
- Zero usable numeric rows -> reason "no_numeric_values" (insufficient evidence)
- Data quality notes from Phase 1-3 profiles and proposals, mentioning outliers and non-numeric exclusions
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from db import Record, Source, SourceVersion, CleaningProposal, QualityReport
from routing.context import StructuredTableSchema

logger = logging.getLogger(__name__)

NUMERIC_REGEX = re.compile(r"^\s*-?[0-9][0-9,]*(\.[0-9]+)?\s*$")
MAX_GROUPS = 50


def _parse_num(val: Any) -> Tuple[str, Optional[float]]:
    """Classify and parse string/numeric value according to standard numeric rules."""
    if val is None:
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


def _evaluate_outliers(
    numeric_items: List[Tuple[float, bool]],
    op: str,
    column: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates outliers on the rows used for a numeric column.
    - If Phase 3 outlier flags exist on the rows used:
        reports: '{count} values in \'{column}\' are flagged as outliers (included in result)'
    - If none exist:
        computes 1.5x IQR bounds on the rows used (read-only)
        if any potential outliers:
            reports: '{count} potential outliers (IQR rule), not flagged'
    - For avg and sum:
        computes excluding_outliers_value and adds note:
        'Excluding {count} outlier values: {clean_val_str}'
    """
    if not numeric_items or not column:
        return {
            "has_outliers": False,
            "outlier_type": None,
            "outliers_count": 0,
            "outlier_notes": [],
            "excluding_outliers_value": None,
            "lower_bound": None,
            "upper_bound": None,
        }

    values = [val for val, _ in numeric_items]
    flagged_mask = [flagged for _, flagged in numeric_items]
    flagged_count = sum(flagged_mask)

    outlier_notes: List[str] = []
    outliers_count = 0
    outlier_type = None
    clean_values = values
    lower_bound = None
    upper_bound = None

    if flagged_count > 0:
        outlier_type = "flagged"
        outliers_count = flagged_count
        outlier_notes.append(f"{flagged_count} values in '{column}' are flagged as outliers (included in result)")
        clean_values = [val for val, flagged in numeric_items if not flagged]
    else:
        # Check IQR rule (1.5x IQR)
        import numpy as np
        if len(values) >= 4:
            arr = np.array(values, dtype=float)
            q25 = float(np.percentile(arr, 25))
            q75 = float(np.percentile(arr, 75))
            iqr = q75 - q25
            lower_bound = q25 - 1.5 * iqr
            upper_bound = q75 + 1.5 * iqr
            iqr_outliers = [v for v in values if v < lower_bound or v > upper_bound]
            if iqr_outliers:
                outlier_type = "iqr"
                outliers_count = len(iqr_outliers)
                outlier_notes.append(f"{outliers_count} potential outliers (IQR rule), not flagged")
                clean_values = [v for v in values if lower_bound <= v <= upper_bound]

    excluding_val = None
    if op in ("avg", "sum") and outliers_count > 0 and clean_values:
        if op == "avg":
            excluding_val = sum(clean_values) / len(clean_values)
        elif op == "sum":
            excluding_val = sum(clean_values)

        if isinstance(excluding_val, float):
            clean_str = f"{int(excluding_val):,}" if excluding_val.is_integer() else f"{excluding_val:,.2f}"
        else:
            clean_str = f"{excluding_val:,}"

        outlier_notes.append(f"Excluding {outliers_count} outlier values: {clean_str}")

    return {
        "has_outliers": (outliers_count > 0),
        "outlier_type": outlier_type,
        "outliers_count": outliers_count,
        "outlier_notes": outlier_notes,
        "excluding_outliers_value": excluding_val,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
    }


def execute_aggregation(
    db: Session,
    table_schema: StructuredTableSchema,
    op: str,                                   # "count" | "sum" | "avg" | "min" | "max"
    column: Optional[str] = None,              # Numeric column for sum/avg/min/max/top_n
    group_by: Optional[str] = None,            # Category column
    filters: Optional[List[Tuple[str, str]]] = None, # (column, value)
    version: Optional[int] = None,
    template: Optional[str] = None,            # "top_n" or None
    top_n: int = 1,                            # Default 1, max 10
) -> Dict[str, Any]:
    """
    Execute deterministic aggregation on records of ONE source.
    Bound parameters only, zero SQL interpolation.
    """
    op = op.lower().strip()
    if op not in ("count", "sum", "avg", "min", "max"):
        raise ValueError(f"Unsupported operation '{op}'.")

    v_no = version if version is not None else table_schema.version
    source_id = table_schema.source_id
    source_name = table_schema.source_name
    input_filters = filters or []

    # 1. Whitelist validation
    whitelisted_cols = set(table_schema.columns)
    if column and column not in whitelisted_cols:
        raise ValueError(f"Target column '{column}' not in schema whitelist.")
    if group_by and group_by not in whitelisted_cols:
        raise ValueError(f"Group-by column '{group_by}' not in schema whitelist.")
    for f_col, _ in input_filters:
        if f_col not in whitelisted_cols:
            raise ValueError(f"Filter column '{f_col}' not in schema whitelist.")

    dialect = db.bind.dialect.name if db.bind else "postgresql"

    # 2. Deduplicate filter values by normalized form (lower/trim)
    # Map (column, norm_val) -> list of original raw values
    norm_filters_map: Dict[Tuple[str, str], List[str]] = {}
    for f_col, f_val in input_filters:
        norm_key = (f_col, str(f_val).strip().lower())
        norm_filters_map.setdefault(norm_key, []).append(str(f_val).strip())

    deduped_filters: List[Dict[str, Any]] = []
    for (f_col, norm_val), raw_vals in norm_filters_map.items():
        canonical_val = raw_vals[0]
        variants = list(dict.fromkeys(raw_vals))

        if dialect == "postgresql":
            try:
                sql_canon = text(
                    "SELECT trim(data ->> :fcol) AS raw_spelling, COUNT(*) AS cnt "
                    "FROM records "
                    "WHERE source_id = :sid AND version_no = :v AND status = 'active' "
                    "  AND lower(trim(data ->> :fcol)) = :nval "
                    "GROUP BY raw_spelling ORDER BY cnt DESC, raw_spelling ASC"
                )
                res_c = db.execute(
                    sql_canon,
                    {"sid": source_id, "v": v_no, "fcol": f_col, "nval": norm_val}
                ).fetchall()
                if res_c:
                    canonical_val = res_c[0][0]
                    variants = [r[0] for r in res_c]
            except Exception as e:
                logger.debug(f"Canonical spelling query failed ({e}), using default.")
        else:
            recs = db.query(Record).filter(
                Record.source_id == source_id,
                Record.version_no == v_no,
                Record.status == "active",
            ).all()
            counts: Dict[str, int] = {}
            for r in recs:
                d = r.data or {}
                raw_v = str(d.get(f_col, "")).strip()
                if raw_v.lower() == norm_val:
                    counts[raw_v] = counts.get(raw_v, 0) + 1
            if counts:
                sorted_s = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
                canonical_val = sorted_s[0][0]
                variants = [s for s, _ in sorted_s]

        deduped_filters.append({
            "column": f_col,
            "value": canonical_val,
            "variants": variants,
        })

    active_filters = [(f["column"], f["value"]) for f in deduped_filters]

    # Build SQL-level description
    filter_desc = " AND ".join(f"{fc} = :param_{i}" for i, (fc, _) in enumerate(active_filters))
    where_desc = "source_id = :sid AND version_no = :v AND status = 'active'"
    if filter_desc:
        where_desc += f" AND {filter_desc}"

    # 3. Handle top_n template
    if template == "top_n":
        if op not in ("max", "min"):
            raise ValueError(f"Template top_n requires op 'max' or 'min', got '{op}'.")
        if not column:
            raise ValueError("Template top_n requires a mapped numeric column.")

        template_name = "top_n"
        top_n = min(max(int(top_n), 1), 10)
        identifier_col = (
            table_schema.identifier_columns[0]
            if table_schema.identifier_columns
            else (table_schema.columns[0] if table_schema.columns else "id")
        )
        display_cols = [c for c in table_schema.columns if c != identifier_col and c != column][:3]

        order_dir = "DESC" if op == "max" else "ASC"
        sql_description = (
            f"SELECT {identifier_col}, {column}, {', '.join(display_cols)} "
            f"FROM records WHERE {where_desc} ORDER BY {column} {order_dir} LIMIT {top_n}"
        )

        rows_considered = 0
        rows_used = 0
        rows_excluded_non_numeric = 0
        rows_null = 0
        parsed_rows: List[Dict[str, Any]] = []

        if dialect == "postgresql":
            params = {
                "sid": source_id,
                "v": v_no,
                "status": "active",
            }
            f_clauses = []
            for i, f in enumerate(deduped_filters):
                params[f"col_{i}"] = f["column"]
                params[f"val_{i}"] = f["value"]
                f_clauses.append(f"lower(trim(data ->> :col_{i})) = lower(trim(:val_{i}))")
            where_f = (" AND " + " AND ".join(f_clauses)) if f_clauses else ""
            sql_records = text(
                f"SELECT id, data, metadata FROM records "
                f"WHERE source_id = :sid AND version_no = :v AND status = :status {where_f}"
            )
            raw_records = db.execute(sql_records, params).fetchall()
            for r_id, r_data, r_meta in raw_records:
                rows_considered += 1
                d = r_data or {}
                meta = r_meta or {}
                val_raw = d.get(column)
                v_type, num = _parse_num(val_raw)
                if v_type == "null":
                    rows_null += 1
                elif v_type == "non_numeric":
                    rows_excluded_non_numeric += 1
                elif v_type == "numeric":
                    rows_used += 1
                    outliers = meta.get("outlier_flags") or []
                    is_outlier = any(
                        isinstance(o, dict) and o.get("column") == column
                        for o in outliers
                    )
                    id_val = str(d.get(identifier_col, ""))
                    parsed_rows.append({
                        "identifier_col": identifier_col,
                        "identifier_value": id_val,
                        "target_col": column,
                        "target_value": num,
                        "display_columns": {c: d.get(c) for c in display_cols},
                        "is_outlier": is_outlier,
                        "val_num": num,
                    })
        else:
            q = db.query(Record).filter(
                Record.source_id == source_id,
                Record.version_no == v_no,
                Record.status == "active",
            )
            all_recs = q.all()
            for r in all_recs:
                d = r.data or {}
                meta = r.metadata_ or {}
                match = True
                for f in deduped_filters:
                    if str(d.get(f["column"], "")).strip().lower() != f["value"].strip().lower():
                        match = False
                        break
                if not match:
                    continue
                rows_considered += 1
                val_raw = d.get(column)
                v_type, num = _parse_num(val_raw)
                if v_type == "null":
                    rows_null += 1
                elif v_type == "non_numeric":
                    rows_excluded_non_numeric += 1
                elif v_type == "numeric":
                    rows_used += 1
                    outliers = meta.get("outlier_flags") or []
                    is_outlier = any(
                        isinstance(o, dict) and o.get("column") == column
                        for o in outliers
                    )
                    id_val = str(d.get(identifier_col, ""))
                    parsed_rows.append({
                        "identifier_col": identifier_col,
                        "identifier_value": id_val,
                        "target_col": column,
                        "target_value": num,
                        "display_columns": {c: d.get(c) for c in display_cols},
                        "is_outlier": is_outlier,
                        "val_num": num,
                    })

        top_rows: List[Dict[str, Any]] = []
        if rows_used == 0:
            reason = "no_numeric_values"
        else:
            reason = None
            if op == "max":
                parsed_rows.sort(key=lambda x: (-x["val_num"], x["identifier_value"]))
            else:
                parsed_rows.sort(key=lambda x: (x["val_num"], x["identifier_value"]))

            unique_vals: List[float] = []
            for r in parsed_rows:
                if r["val_num"] not in unique_vals:
                    unique_vals.append(r["val_num"])

            top_vals_set = set(unique_vals[:top_n])
            tied_rows = [r for r in parsed_rows if r["val_num"] in top_vals_set]
            top_rows = tied_rows[:10]

        used_numeric_items = [(r["val_num"], r["is_outlier"]) for r in parsed_rows]
        outlier_info = _evaluate_outliers(used_numeric_items, op, column)

        for r in top_rows:
            if outlier_info["outlier_type"] == "flagged":
                if r.get("is_outlier"):
                    r["outlier_annotation"] = "Phase 3 outlier flag"
            elif outlier_info["outlier_type"] == "iqr":
                lo, hi = outlier_info["lower_bound"], outlier_info["upper_bound"]
                if lo is not None and hi is not None and (r["val_num"] < lo or r["val_num"] > hi):
                    r["is_iqr_outlier"] = True
                    r["outlier_annotation"] = "potential outlier (IQR rule)"

        # 4. Outlier and non-numeric counts in Data Quality Notes
        data_quality_notes = _build_data_quality_notes(
            db=db,
            source_id=source_id,
            v_no=v_no,
            used_columns={column} | {fc for fc, _ in active_filters},
            column=column,
            dialect=dialect,
            rows_excluded_non_numeric=rows_excluded_non_numeric,
            outlier_notes=outlier_info["outlier_notes"],
        )

        return {
            "success": (reason is None),
            "reason": reason,
            "template": template_name,
            "source_id": source_id,
            "source_name": source_name,
            "version": v_no,
            "column": column,
            "op": op,
            "group_by": None,
            "filters": deduped_filters,
            "rows_considered": rows_considered,
            "rows_used": rows_used,
            "rows_excluded_non_numeric": rows_excluded_non_numeric,
            "rows_null": rows_null,
            "result_value": top_rows[0]["target_value"] if top_rows else None,
            "excluding_outliers_value": outlier_info.get("excluding_outliers_value"),
            "outliers_count": outlier_info.get("outliers_count", 0),
            "groups": [],
            "groups_cut": 0,
            "top_rows": top_rows,
            "top_n": top_n,
            "identifier_column": identifier_col,
            "display_columns": display_cols,
            "data_quality_notes": data_quality_notes,
            "sql_description": sql_description,
        }

    # 4. Standard Aggregations (count, sum, avg, min, max)
    if group_by:
        if op == "count" and not column:
            sql_description = f"SELECT {group_by}, COUNT(*) FROM records WHERE {where_desc} GROUP BY {group_by}"
            template_name = "count_group_by"
        else:
            sql_description = f"SELECT {group_by}, {op.upper()}(clean_numeric({column})) FROM records WHERE {where_desc} GROUP BY {group_by}"
            template_name = f"{op}_group_by"
    else:
        if op == "count" and not column:
            sql_description = f"SELECT COUNT(*) FROM records WHERE {where_desc}"
            template_name = "count"
        else:
            sql_description = f"SELECT {op.upper()}(clean_numeric({column})) FROM records WHERE {where_desc}"
            template_name = op

    rows_considered = 0
    rows_used = 0
    rows_excluded_non_numeric = 0
    rows_null = 0
    result_value: Optional[float] = None
    groups: List[Dict[str, Any]] = []
    groups_cut = 0
    used_numeric_items: List[Tuple[float, bool]] = []

    if dialect == "postgresql":
        params: Dict[str, Any] = {
            "source_id": source_id,
            "version_no": v_no,
            "status": "active",
        }
        filter_clauses = []
        for i, (f_col, f_val) in enumerate(active_filters):
            col_key = f"fcol_{i}"
            val_key = f"fval_{i}"
            params[col_key] = f_col
            params[val_key] = f_val
            filter_clauses.append(f"lower(trim(data ->> :{col_key})) = lower(trim(:{val_key}))")

        filter_sql = (" AND " + " AND ".join(filter_clauses)) if filter_clauses else ""
        col_expr = "data ->> :col_target" if column else "NULL"
        if column:
            params["col_target"] = column

        if group_by:
            params["col_grp"] = group_by
            grp_expr = "trim(data ->> :col_grp)"
            select_grp = f"{grp_expr} AS grp_raw,"
            grp_by_clause = "GROUP BY grp_raw ORDER BY count_val DESC, grp_raw ASC"
            grp_select_out = "grp_raw AS group_key,"
        else:
            select_grp = ""
            grp_by_clause = ""
            grp_select_out = ""

        cte = f"""
        WITH filtered_rows AS (
            SELECT
                {col_expr} AS val_raw,
                {select_grp}
                1 AS row_marker
            FROM records
            WHERE source_id = :source_id
              AND version_no = :version_no
              AND status = :status
              {filter_sql}
        ),
        classified AS (
            SELECT
                val_raw,
                {"grp_raw," if group_by else ""}
                CASE
                    WHEN val_raw IS NULL OR trim(val_raw) = '' THEN 'null'
                    WHEN val_raw ~ '^\\s*-?[0-9][0-9,]*(\\.[0-9]+)?\\s*$' THEN 'numeric'
                    ELSE 'non_numeric'
                END AS val_type,
                CASE
                    WHEN val_raw ~ '^\\s*-?[0-9][0-9,]*(\\.[0-9]+)?\\s*$'
                    THEN CAST(replace(trim(val_raw), ',', '') AS DOUBLE PRECISION)
                    ELSE NULL
                END AS val_num
            FROM filtered_rows
        )
        SELECT
            {grp_select_out}
            COUNT(*) AS rows_considered,
            COUNT(*) FILTER (WHERE val_type = 'numeric') AS rows_used,
            COUNT(*) FILTER (WHERE val_type = 'non_numeric') AS rows_excluded,
            COUNT(*) FILTER (WHERE val_type = 'null') AS rows_null,
            AVG(val_num) AS avg_val,
            SUM(val_num) AS sum_val,
            MIN(val_num) AS min_val,
            MAX(val_num) AS max_val,
            COUNT(*) AS count_val
        FROM classified
        {grp_by_clause}
        """

        res = db.execute(text(cte), params).fetchall()

        if group_by:
            total_considered = 0
            total_used = 0
            total_excluded = 0
            total_null = 0
            raw_groups = []

            for r in res:
                g_key = r[0] if r[0] is not None else "(empty)"
                g_considered = int(r[1])
                g_used = int(r[2])
                g_excluded = int(r[3])
                g_null = int(r[4])
                avg_v = float(r[5]) if r[5] is not None else None
                sum_v = float(r[6]) if r[6] is not None else None
                min_v = float(r[7]) if r[7] is not None else None
                max_v = float(r[8]) if r[8] is not None else None
                cnt_v = int(r[9])

                total_considered += g_considered
                total_used += g_used if op != "count" else g_considered
                total_excluded += g_excluded
                total_null += g_null

                val_map = {
                    "count": cnt_v,
                    "avg": avg_v,
                    "sum": sum_v,
                    "min": min_v,
                    "max": max_v,
                }
                raw_groups.append({
                    "group": g_key,
                    "value": val_map.get(op),
                    "rows_considered": g_considered,
                    "rows_used": g_used if op != "count" else g_considered,
                    "rows_excluded_non_numeric": g_excluded,
                })

            rows_considered = total_considered
            rows_used = total_used
            rows_excluded_non_numeric = total_excluded
            rows_null = total_null

            if len(raw_groups) > MAX_GROUPS:
                groups = raw_groups[:MAX_GROUPS]
                groups_cut = len(raw_groups) - MAX_GROUPS
            else:
                groups = raw_groups
                groups_cut = 0
        else:
            if res:
                r = res[0]
                rows_considered = int(r[0])
                rows_used = int(r[1])
                rows_excluded_non_numeric = int(r[2])
                rows_null = int(r[3])
                avg_v = float(r[4]) if r[4] is not None else None
                sum_v = float(r[5]) if r[5] is not None else None
                min_v = float(r[6]) if r[6] is not None else None
                max_v = float(r[7]) if r[7] is not None else None
                cnt_v = int(r[8])

                if op == "count":
                    rows_used = rows_considered
                    result_value = cnt_v
                elif op == "avg":
                    result_value = avg_v
                elif op == "sum":
                    result_value = sum_v
                elif op == "min":
                    result_value = min_v
                elif op == "max":
                    result_value = max_v

            if column and rows_used > 0:
                sql_col_rows = text(
                    f"SELECT data ->> :col_target AS val_raw, metadata FROM records "
                    f"WHERE source_id = :source_id AND version_no = :version_no AND status = :status {filter_sql}"
                )
                raw_col_rows = db.execute(sql_col_rows, params).fetchall()
                for val_raw, meta in raw_col_rows:
                    v_type, num = _parse_num(val_raw)
                    if v_type == "numeric":
                        oflags = (meta or {}).get("outlier_flags") or []
                        is_fl = any(isinstance(o, dict) and o.get("column") == column for o in oflags)
                        used_numeric_items.append((num, is_fl))

    else:
        # SQLite dialect fallback for in-memory unit tests
        q = db.query(Record).filter(
            Record.source_id == source_id,
            Record.version_no == v_no,
            Record.status == "active",
        )
        all_records = q.all()

        filtered_records = []
        for r in all_records:
            d = r.data or {}
            match = True
            for fc, fv in active_filters:
                v_act = str(d.get(fc, "")).strip().lower()
                if v_act != fv.strip().lower():
                    match = False
                    break
            if match:
                filtered_records.append(r)

        rows_considered = len(filtered_records)

        if group_by:
            from collections import defaultdict
            grp_data = defaultdict(list)
            for r in filtered_records:
                d = r.data or {}
                gk = str(d.get(group_by, "")).strip() or "(empty)"
                grp_data[gk].append(d)

            raw_groups = []
            for gk, recs in grp_data.items():
                g_considered = len(recs)
                g_used = 0
                g_excl = 0
                g_null = 0
                nums = []
                for d in recs:
                    v_type, num = _parse_num(d.get(column)) if column else ("numeric", 1.0)
                    if v_type == "numeric":
                        g_used += 1
                        if num is not None:
                            nums.append(num)
                    elif v_type == "non_numeric":
                        g_excl += 1
                    else:
                        g_null += 1

                rows_used += g_used if op != "count" else g_considered
                rows_excluded_non_numeric += g_excl
                rows_null += g_null

                val = None
                if op == "count":
                    val = g_considered
                elif nums:
                    if op == "sum":
                        val = sum(nums)
                    elif op == "avg":
                        val = sum(nums) / len(nums)
                    elif op == "min":
                        val = min(nums)
                    elif op == "max":
                        val = max(nums)

                raw_groups.append({
                    "group": gk,
                    "value": val,
                    "rows_considered": g_considered,
                    "rows_used": g_used if op != "count" else g_considered,
                    "rows_excluded_non_numeric": g_excl,
                })

            raw_groups.sort(key=lambda x: (-(x["rows_considered"]), x["group"]))
            if len(raw_groups) > MAX_GROUPS:
                groups = raw_groups[:MAX_GROUPS]
                groups_cut = len(raw_groups) - MAX_GROUPS
            else:
                groups = raw_groups
                groups_cut = 0

        else:
            nums = []
            for r in filtered_records:
                d = r.data or {}
                meta = r.metadata_ or {}
                if op == "count" and not column:
                    rows_used += 1
                    continue
                v_type, num = _parse_num(d.get(column))
                if v_type == "numeric":
                    rows_used += 1
                    if num is not None:
                        nums.append(num)
                        oflags = meta.get("outlier_flags") or []
                        is_fl = any(isinstance(o, dict) and o.get("column") == column for o in oflags)
                        used_numeric_items.append((num, is_fl))
                elif v_type == "non_numeric":
                    rows_excluded_non_numeric += 1
                else:
                    rows_null += 1

            if op == "count":
                rows_used = rows_considered
                result_value = rows_considered
            elif nums:
                if op == "sum":
                    result_value = sum(nums)
                elif op == "avg":
                    result_value = sum(nums) / len(nums)
                elif op == "min":
                    result_value = min(nums)
                elif op == "max":
                    result_value = max(nums)

    outlier_info = _evaluate_outliers(used_numeric_items, op, column)

    # 5. Check for zero usable numeric rows
    reason = None
    if op in ("sum", "avg", "min", "max") and rows_used == 0:
        reason = "no_numeric_values"

    used_columns = set()
    if column:
        used_columns.add(column)
    if group_by:
        used_columns.add(group_by)
    for fc, _ in active_filters:
        used_columns.add(fc)

    data_quality_notes = _build_data_quality_notes(
        db=db,
        source_id=source_id,
        v_no=v_no,
        used_columns=used_columns,
        column=column,
        dialect=dialect,
        rows_excluded_non_numeric=rows_excluded_non_numeric,
        outlier_notes=outlier_info["outlier_notes"],
    )

    return {
        "success": (reason is None),
        "reason": reason,
        "template": template_name,
        "source_id": source_id,
        "source_name": source_name,
        "version": v_no,
        "column": column,
        "op": op,
        "group_by": group_by,
        "filters": deduped_filters,
        "rows_considered": rows_considered,
        "rows_used": rows_used,
        "rows_excluded_non_numeric": rows_excluded_non_numeric,
        "rows_null": rows_null,
        "result_value": result_value,
        "excluding_outliers_value": outlier_info.get("excluding_outliers_value"),
        "outliers_count": outlier_info.get("outliers_count", 0),
        "groups": groups,
        "groups_cut": groups_cut,
        "top_rows": [],
        "top_n": None,
        "identifier_column": None,
        "display_columns": [],
        "data_quality_notes": data_quality_notes,
        "sql_description": sql_description,
    }


def _build_data_quality_notes(
    db: Session,
    source_id: int,
    v_no: int,
    used_columns: Set[str],
    column: Optional[str],
    dialect: str,
    rows_excluded_non_numeric: int,
    outlier_notes: Optional[List[str]] = None,
) -> List[str]:
    """Helper to compile data quality notes including outlier and non-numeric counts."""
    data_quality_notes: List[str] = []

    # Outliers in numeric column used (from evaluation on rows used)
    if outlier_notes is not None:
        data_quality_notes.extend(outlier_notes)
    elif column:
        outlier_count = 0
        try:
            if dialect == "postgresql":
                sql_outliers = text(
                    "SELECT COUNT(*) FROM records "
                    "WHERE source_id = :sid AND version_no = :v AND status = 'active' "
                    "  AND metadata -> 'outlier_flags' IS NOT NULL "
                    "  AND EXISTS ( "
                    "    SELECT 1 FROM jsonb_array_elements(metadata -> 'outlier_flags') elem "
                    "    WHERE elem ->> 'column' = :col "
                    "  )"
                )
                outlier_count = db.execute(sql_outliers, {"sid": source_id, "v": v_no, "col": column}).scalar() or 0
            else:
                all_v_recs = db.query(Record).filter(
                    Record.source_id == source_id, Record.version_no == v_no, Record.status == "active"
                ).all()
                for r in all_v_recs:
                    m = r.metadata_ or {}
                    oflags = m.get("outlier_flags", [])
                    if any(isinstance(o, dict) and o.get("column") == column for o in oflags):
                        outlier_count += 1
        except Exception as e:
            logger.debug(f"Outlier count check error: {e}")

        if outlier_count > 0:
            data_quality_notes.append(f"{outlier_count} values in '{column}' are flagged as outliers (included in result)")

        if rows_excluded_non_numeric > 0:
            data_quality_notes.append(f"{rows_excluded_non_numeric} rows had non-numeric values in '{column}' and were excluded")

    # Dataset profile notes
    sv = (
        db.query(SourceVersion)
        .filter(SourceVersion.source_id == source_id, SourceVersion.version_no == v_no)
        .first()
    )
    profile = sv.profile if sv and sv.profile else {}
    if not profile or not profile.get("columns"):
        source_rec = db.query(Source).filter(Source.id == source_id).first()
        if source_rec and source_rec.file_id:
            qr = (
                db.query(QualityReport)
                .filter(QualityReport.file_id == source_rec.file_id)
                .order_by(QualityReport.id.desc())
                .first()
            )
            if qr and qr.report:
                profile = qr.report

    dup_rows = profile.get("duplicate_rows", 0)
    col_stats = profile.get("columns", {})

    pending_critical = (
        db.query(func.count(CleaningProposal.id))
        .filter(
            CleaningProposal.source_id == source_id,
            CleaningProposal.base_version == v_no,
            CleaningProposal.status == "pending",
            CleaningProposal.severity == "critical",
        )
        .scalar()
        or 0
    )

    if dup_rows > 0:
        data_quality_notes.append(f"{dup_rows} duplicate rows detected in dataset")

    for uc in sorted(used_columns):
        missing_pct = col_stats.get(uc, {}).get("missing_pct", 0.0)
        if missing_pct > 0:
            data_quality_notes.append(f"Column '{uc}' has {missing_pct}% missing values")

    if pending_critical > 0:
        data_quality_notes.append(f"{pending_critical} pending critical cleaning proposals exist for this dataset")

    has_quality_issues = (dup_rows > 0) or any(col_stats.get(uc, {}).get("missing_pct", 0) > 0 for uc in used_columns) or (pending_critical > 0)
    if v_no == 1 and has_quality_issues:
        data_quality_notes.insert(0, "Warning: Query executed on uncleaned data (Version 1). Known quality issues exist.")

    return data_quality_notes
