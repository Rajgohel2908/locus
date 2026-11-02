"""
routing/context.py — Database-facing schema context for query routing.

Builds a KBSchemaContext for the requested source_ids:
- For each structured source, latest (or requested) version, active rows only.
- Column names, column roles (from column_roles / profile), dtypes.
- Distinct values of category columns (capped at 200 per column).
- resolve_identifiers(tokens): Checks tokens against identifier-column values
  using a bound-parameter SQL lookup (zero table scan in Python).
- Clean separation from pure logic so tests can inject a fake context.
"""

from typing import List, Dict, Any, Optional, Set, Callable
import logging
import re
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from db import Source, Record, SourceVersion, ColumnRole, QualityReport

logger = logging.getLogger(__name__)


@dataclass
class StructuredTableSchema:
    source_id: int
    source_name: str
    version: int
    columns: List[str]
    column_roles: Dict[str, str]           # col -> role (identifier, category, numeric, date, etc.)
    dtypes: Dict[str, str]                 # col -> dtype
    category_values: Dict[str, List[str]]  # col -> list of distinct string values (cap 200)
    identifier_columns: List[str]          # columns with identifier role
    numeric_columns: List[str]             # columns with numeric role or numeric dtype


@dataclass
class KBSchemaContext:
    tables: Dict[int, StructuredTableSchema] = field(default_factory=dict)
    all_source_ids: List[int] = field(default_factory=list)
    custom_identifier_resolver: Optional[Callable[[List[str]], Set[str]]] = None
    _db: Optional[Session] = None

    @property
    def structured_source_ids(self) -> List[int]:
        return list(self.tables.keys())

    def resolve_identifiers(self, tokens: List[str]) -> Set[str]:
        """
        Check tokens against identifier-column values with a bound-parameter SQL lookup.
        Zero table scan in Python.
        """
        if not tokens:
            return set()

        if self.custom_identifier_resolver is not None:
            return self.custom_identifier_resolver(tokens)

        if not self._db or not self.tables:
            return set()

        hits = set()
        clean_tokens = [t.lower().strip() for t in tokens if t.strip()]
        if not clean_tokens:
            return set()

        dialect = self._db.bind.dialect.name if self._db.bind else "postgresql"

        for sid, table in self.tables.items():
            if not table.identifier_columns:
                continue

            for id_col in table.identifier_columns:
                try:
                    if dialect == "postgresql":
                        stmt = text(
                            "SELECT DISTINCT data ->> :col AS val "
                            "FROM records "
                            "WHERE source_id = :sid "
                            "  AND version_no = :v "
                            "  AND status = 'active' "
                            "  AND lower(trim(data ->> :col)) = ANY(:tokens)"
                        )
                        rows = self._db.execute(
                            stmt,
                            {"sid": sid, "v": table.version, "col": id_col, "tokens": clean_tokens}
                        ).fetchall()
                    else:
                        # SQLite fallback for in-memory unit tests
                        in_params = {f"t_{i}": tok for i, tok in enumerate(clean_tokens)}
                        placeholders = ", ".join(f":t_{i}" for i in range(len(clean_tokens)))
                        stmt_str = (
                            f"SELECT DISTINCT json_extract(data, '$.' || :col) AS val "
                            f"FROM records "
                            f"WHERE source_id = :sid "
                            f"  AND version_no = :v "
                            f"  AND status = 'active' "
                            f"  AND lower(trim(json_extract(data, '$.' || :col))) IN ({placeholders})"
                        )
                        stmt = text(stmt_str)
                        params = {"sid": sid, "v": table.version, "col": id_col, **in_params}
                        rows = self._db.execute(stmt, params).fetchall()

                    for r in rows:
                        if r[0]:
                            hits.add(str(r[0]).lower().strip())
                except Exception as e:
                    logger.warning(f"Error resolving identifiers for column {id_col} in source {sid}: {e}")

        return hits


def build_schema_context(
    db: Session,
    source_ids: Optional[List[int]] = None,
    version: Optional[int] = None,
) -> KBSchemaContext:
    """
    Build KBSchemaContext from DB for the specified source_ids and optional version.
    """
    q_src = db.query(Source)
    if source_ids:
        q_src = q_src.filter(Source.id.in_(source_ids))
    sources = q_src.all()

    tables: Dict[int, StructuredTableSchema] = {}
    dialect = db.bind.dialect.name if db.bind else "postgresql"

    for s in sources:
        # Determine if this source has records
        rec_count = db.query(func.count(Record.id)).filter(Record.source_id == s.id).scalar() or 0
        if rec_count == 0:
            continue

        # Resolve version
        if version is not None:
            v_no = version
        else:
            max_v = (
                db.query(func.max(SourceVersion.version_no))
                .filter(SourceVersion.source_id == s.id)
                .scalar()
            )
            if max_v is None:
                max_v = (
                    db.query(func.max(Record.version_no))
                    .filter(Record.source_id == s.id)
                    .scalar()
                )
            v_no = max_v or 1

        # Load roles
        role_rows = db.query(ColumnRole).filter(ColumnRole.source_id == s.id).all()
        roles_dict = {r.column_name: r.role.lower() for r in role_rows}

        # Load profile
        sv = (
            db.query(SourceVersion)
            .filter(SourceVersion.source_id == s.id, SourceVersion.version_no == v_no)
            .first()
        )
        profile = sv.profile if sv and sv.profile else {}
        if not profile or not profile.get("columns"):
            if s.file_id:
                qr = (
                    db.query(QualityReport)
                    .filter(QualityReport.file_id == s.file_id)
                    .order_by(QualityReport.id.desc())
                    .first()
                )
                if qr and qr.report:
                    profile = qr.report

        columns_profile = profile.get("columns", {})

        # Determine column list: union of profile columns, record keys, and role keys
        col_set = set()
        if columns_profile:
            col_set.update(columns_profile.keys())
        first_rec = (
            db.query(Record.data)
            .filter(Record.source_id == s.id, Record.version_no == v_no, Record.status == "active")
            .first()
        )
        if first_rec and first_rec[0]:
            col_set.update(first_rec[0].keys())
        col_set.update(roles_dict.keys())

        # Preserve canonical order: record data keys first, then profile keys, then any remaining
        if first_rec and first_rec[0]:
            columns = [c for c in first_rec[0].keys() if c in col_set]
            for c in sorted(col_set - set(columns)):
                columns.append(c)
        elif columns_profile:
            columns = [c for c in columns_profile.keys() if c in col_set]
            for c in sorted(col_set - set(columns)):
                columns.append(c)
        else:
            columns = sorted(list(col_set))

        num_pattern = re.compile(r"^\s*-?[0-9][0-9,]*(\.[0-9]+)?\s*$")
        common_num_names = {"salary", "amount", "price", "cost", "budget", "age", "revenue", "expense", "balance", "total", "count", "pay", "rate", "wage", "bonus"}

        dtypes_dict: Dict[str, str] = {}
        numeric_cols: List[str] = []
        identifier_cols: List[str] = []

        for c in columns:
            cp = columns_profile.get(c, {})
            dtypes_dict[c] = cp.get("dtype", "object")
            dt = dtypes_dict[c].lower()
            role = roles_dict.get(c, "").lower()

            if role == "identifier" or (not role and any(id_hint in c.lower() for id_hint in ["id", "code", "uuid"])):
                roles_dict[c] = "identifier"
                identifier_cols.append(c)
                continue

            if role == "numeric" or "float" in dt or "int" in dt:
                roles_dict[c] = "numeric"
                numeric_cols.append(c)
                continue

            # If not an identifier or date, check if column is numeric via common names or sample records
            if role not in ("date", "category"):
                is_num = any(name in c.lower() for name in common_num_names)
                if not is_num:
                    try:
                        if dialect == "postgresql":
                            sample_rows = db.execute(
                                text("SELECT data ->> :col FROM records WHERE source_id = :sid AND version_no = :v AND status = 'active' AND data ->> :col IS NOT NULL LIMIT 10"),
                                {"sid": s.id, "v": v_no, "col": c}
                            ).fetchall()
                        else:
                            sample_rows = db.execute(
                                text("SELECT json_extract(data, '$.' || :col) FROM records WHERE source_id = :sid AND version_no = :v AND status = 'active' AND json_extract(data, '$.' || :col) IS NOT NULL LIMIT 10"),
                                {"sid": s.id, "v": v_no, "col": c}
                            ).fetchall()
                        if sample_rows:
                            numeric_samples = sum(1 for r in sample_rows if r[0] and num_pattern.match(str(r[0])))
                            if (numeric_samples / len(sample_rows)) >= 0.5:
                                is_num = True
                    except Exception:
                        pass

                if is_num:
                    roles_dict[c] = "numeric"
                    numeric_cols.append(c)
                    continue

            if not role:
                roles_dict[c] = "category"

        category_cols = [
            c for c in columns
            if c not in numeric_cols and c not in identifier_cols and roles_dict.get(c) != "date"
        ]

        # Fetch distinct category values (capped at 200 per column)
        category_values: Dict[str, List[str]] = {}
        for c in category_cols:
            try:
                if dialect == "postgresql":
                    stmt = text(
                        "SELECT DISTINCT trim(data ->> :col) AS val "
                        "FROM records "
                        "WHERE source_id = :sid "
                        "  AND version_no = :v "
                        "  AND status = 'active' "
                        "  AND data ->> :col IS NOT NULL "
                        "  AND trim(data ->> :col) != '' "
                        "LIMIT 200"
                    )
                    vals = [r[0] for r in db.execute(stmt, {"sid": s.id, "v": v_no, "col": c}).fetchall() if r[0]]
                else:
                    stmt = text(
                        "SELECT DISTINCT trim(json_extract(data, '$.' || :col)) AS val "
                        "FROM records "
                        "WHERE source_id = :sid "
                        "  AND version_no = :v "
                        "  AND status = 'active' "
                        "  AND json_extract(data, '$.' || :col) IS NOT NULL "
                        "  AND trim(json_extract(data, '$.' || :col)) != '' "
                        "LIMIT 200"
                    )
                    vals = [r[0] for r in db.execute(stmt, {"sid": s.id, "v": v_no, "col": c}).fetchall() if r[0]]
                category_values[c] = vals
            except Exception as e:
                logger.warning(f"Could not load category values for column {c} in source {s.id}: {e}")
                category_values[c] = []

        tables[s.id] = StructuredTableSchema(
            source_id=s.id,
            source_name=s.name or f"source_{s.id}",
            version=v_no,
            columns=columns,
            column_roles=roles_dict,
            dtypes=dtypes_dict,
            category_values=category_values,
            identifier_columns=identifier_cols,
            numeric_columns=numeric_cols,
        )

    all_sids = [s.id for s in sources] if sources else (source_ids or [])
    return KBSchemaContext(
        tables=tables,
        all_source_ids=all_sids,
        _db=db,
    )
