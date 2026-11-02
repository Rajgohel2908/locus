"""
structured/render.py — Pure deterministic text renderer for structured query results.

Produces clean, human-readable answers in English with full lineage metadata,
row counts, non-numeric exclusion notes, and data quality warnings.
Zero LLM calls.
"""

from typing import Dict, Any


def render_answer(result: Dict[str, Any]) -> str:
    """
    Renders structured query result into a clean, deterministic English answer string.
    Example:
    "Average Salary where City = Mumbai: 54,200.50 (computed from 37 active rows of employees_messy.csv v2; 3 rows had non-numeric values and were excluded)"
    """
    template = result.get("template", "")
    op = result.get("op", "count").lower()
    op_labels = {
        "count": "Count",
        "sum": "Total",
        "avg": "Average",
        "min": "Minimum",
        "max": "Maximum",
    }
    op_label = op_labels.get(op, op.capitalize())

    col = result.get("column")
    col_str = f" {col}" if col else (" of records" if op == "count" and not result.get("group_by") else "")

    # Filters rendering with canonical spelling and spelling variants
    filters = result.get("filters", [])
    filter_parts = []
    for f in filters:
        col_name = f.get("column", "")
        val_name = f.get("value", "")
        variants = f.get("variants", [])
        if len(variants) > 1:
            var_str = ", ".join(variants)
            filter_parts.append(f"{col_name} = {val_name} (matched {len(variants)} spelling variants: {var_str})")
        else:
            filter_parts.append(f"{col_name} = {val_name}")

    where_str = f" where {' and '.join(filter_parts)}" if filter_parts else ""

    # Lineage and accounting notes
    rows_used = result.get("rows_used", 0)
    source_name = result.get("source_name", "dataset")
    version = result.get("version", 1)
    meta_parts = [f"computed from {rows_used} active rows of {source_name} v{version}"]

    excl = result.get("rows_excluded_non_numeric", 0)
    if excl > 0:
        meta_parts.append(f"{excl} rows had non-numeric values and were excluded")

    # Bug 3(a): Never print "N rows were null" for count templates without a column;
    # print null counts only for column templates and only when > 0.
    nulls = result.get("rows_null", 0)
    if col and nulls > 0:
        meta_parts.append(f"{nulls} rows were null")

    meta_str = "; ".join(meta_parts)

    group_by = result.get("group_by")
    lines = []

    if template == "top_n":
        top_rows = result.get("top_rows", [])
        top_n = result.get("top_n", 1)
        col_display = col or "value"
        if op == "max":
            title = f"Top {top_n} Highest {col_display}" if top_n > 1 else f"Highest {col_display}"
        else:
            title = f"Top {top_n} Lowest {col_display}" if top_n > 1 else f"Lowest {col_display}"

        lines.append(f"{title}{where_str}:")
        for r in top_rows:
            id_val = r.get("identifier_value", "")
            t_val = r.get("target_value")
            if isinstance(t_val, float):
                t_val_str = f"{int(t_val):,}" if t_val.is_integer() else f"{t_val:,.2f}"
            elif isinstance(t_val, int):
                t_val_str = f"{t_val:,}"
            else:
                t_val_str = str(t_val)

            disp_dict = r.get("display_columns", {})
            disp_parts = [f"{k}: {v}" for k, v in disp_dict.items() if v is not None and str(v).strip()]
            disp_str = f" ({', '.join(disp_parts)})" if disp_parts else ""
            outlier_str = ""
            if r.get("is_outlier") or r.get("outlier_annotation") == "Phase 3 outlier flag":
                outlier_str = " [Phase 3 outlier flag]"
            elif r.get("is_iqr_outlier") or r.get("outlier_annotation") == "potential outlier (IQR rule)":
                outlier_str = " [potential outlier (IQR rule)]"
            lines.append(f"- {id_val}: {col_display} {t_val_str}{disp_str}{outlier_str}")

        lines.append(f"({meta_str})")

    elif group_by:
        header = f"{op_label}{col_str} by {group_by}{where_str}:"
        lines.append(header)
        for g in result.get("groups", []):
            val = g.get("value")
            if val is None:
                val_str = "None"
            elif isinstance(val, float):
                val_str = f"{val:,.2f}"
            elif isinstance(val, int):
                val_str = f"{val:,}"
            else:
                val_str = str(val)

            g_used = g.get("rows_used", 0)
            lines.append(f"- {g['group']}: {val_str} ({g_used} active rows)")

        groups_cut = result.get("groups_cut", 0)
        if groups_cut > 0:
            lines.append(f"- ... ({groups_cut} additional groups cut)")

        lines.append(f"({meta_str})")

    else:
        val = result.get("result_value")
        if val is None:
            val_str = "None"
        elif isinstance(val, float):
            val_str = f"{val:,.2f}"
        elif isinstance(val, int):
            val_str = f"{val:,}"
        else:
            val_str = str(val)

        main_text = f"{op_label}{col_str}{where_str}: {val_str} ({meta_str})"
        lines.append(main_text)

        if op in ("avg", "sum") and result.get("excluding_outliers_value") is not None:
            ex_count = result.get("outliers_count", 0)
            ex_val = result["excluding_outliers_value"]
            if isinstance(ex_val, float):
                ex_val_str = f"{int(ex_val):,}" if ex_val.is_integer() else f"{ex_val:,.2f}"
            elif isinstance(ex_val, int):
                ex_val_str = f"{ex_val:,}"
            else:
                ex_val_str = str(ex_val)
            lines.append(f"Excluding {ex_count} outlier values: {ex_val_str}")

    # Append quality notes if present
    notes = result.get("data_quality_notes", [])
    if notes:
        lines.append("\nData Quality Notes:")
        for note in notes:
            lines.append(f"- {note}")

    return "\n".join(lines)
