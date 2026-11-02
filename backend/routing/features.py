"""
routing/features.py — Pure feature extraction for query analysis.

Extracts deterministic query features from question and KBSchemaContext:
- identifier_candidates (letters + digits) and identifier_hits (found in ID columns)
- aggregation_intent {op: count|sum|avg|min|max, matched_phrase} in English/Hinglish
- group_by_hint ("per X", "by X", "each X", "every X", "har X" mapped to category column)
- row_identity_request ("who", "which", "kaun", "kiski")
- comparison_intent and multi_part (2+ ?, 2+ interrogatives, >25 words)
- mapped_columns (camelCase/snake_case splitting, stemming, plural stripping, edit dist <= 1)
- filter_values (1-3 word category value matches)
- mappable flag with diagnostic reason code
"""

import re
from typing import List, Dict, Any, Optional, Tuple, Set
from pydantic import BaseModel, ConfigDict, Field

from retrieval.lexical import tokenize
from routing.context import KBSchemaContext, StructuredTableSchema


class AggregationIntent(BaseModel):
    op: str  # count | sum | avg | min | max
    matched_phrase: str


class ColumnMatch(BaseModel):
    column: str
    source_id: int
    matched_token: str
    role: str


class FilterValueMatch(BaseModel):
    column: str
    value: str
    source_id: int


class QueryFeatures(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: str
    identifier_candidates: List[str] = Field(default_factory=list)
    identifier_hits: List[str] = Field(default_factory=list)
    aggregation_intent: Optional[AggregationIntent] = None
    group_by_hint: Optional[str] = None
    row_identity_request: bool = False
    comparison_intent: bool = False
    multi_part: bool = False
    mapped_columns: List[ColumnMatch] = Field(default_factory=list)
    filter_values: List[FilterValueMatch] = Field(default_factory=list)
    unmapped_terms: List[str] = Field(default_factory=list)
    top_n: int = 1
    mappable: bool = False
    mappable_reason: str = "uninitialized"
    target_source_id: Optional[int] = None
    target_column: Optional[str] = None


# ── String & Stemming Helpers ────────────────────────────────────────────────

def _naive_stem(word: str) -> str:
    """Strips trailing possessives and naive plural suffixes."""
    w = word.lower().strip()
    if w.endswith("'s") or w.endswith("’s"):
        w = w[:-2]
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("es") and len(w) > 3:
        # e.g., policies -> policy, leaves -> leave / leav
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    return w


def _split_column_name(name: str) -> List[str]:
    """Splits column names on underscores, spaces, and camelCase transitions."""
    # Split camelCase: e.g. annualLeaves -> annual Leaves, EmployeeID -> Employee ID
    s1 = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', name)
    s2 = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', s1)
    # Split on non-alphanumeric
    parts = re.split(r'[^a-zA-Z0-9]+', s2)
    return [p.lower() for p in parts if p.strip()]


def _levenshtein(s1: str, s2: str) -> int:
    """Compute standard Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)

    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev[j + 1] + 1
            deletions = curr[j] + 1
            substitutions = prev[j] + (0 if c1 == c2 else 1)
            curr.append(min(insertions, deletions, substitutions))
        prev = curr
    return prev[-1]


# ── Interrogatives & Comparison Patterns ─────────────────────────────────────

INTERROGATIVES = [
    "who", "what", "where", "when", "why", "how", "which", "whom", "whose",
    "kya", "kaun", "kab", "kaha", "kahan", "kyu", "kyun", "kaise", "kitna", "kitne", "kitni"
]

ROW_IDENTITY_RE = re.compile(
    r"\b(who|which|kaun|kiska|kiski|kiske)\b",
    re.IGNORECASE
)

COMPARISON_RE = re.compile(
    r"\b(compare|versus|vs\.?|difference\s+between|better\s+than|tulna|antar)\b",
    re.IGNORECASE
)

# Ordered aggregation phrases: checked from most specific to least specific
AGGREGATION_PHRASES: List[Tuple[str, str, re.Pattern]] = [
    # (op, phrase_label, compiled_regex)
    ("avg", "average of", re.compile(r"\b(average\s+of|avg\s+of|mean\s+of)\b", re.IGNORECASE)),
    ("avg", "average", re.compile(r"\b(average|avg|mean|ausat)\b", re.IGNORECASE)),
    ("max", "highest", re.compile(r"\b(highest|maximum|max|sabse\s+zyada|sabse\s+jyada|sabse\s+adhik|adhiktam)\b", re.IGNORECASE)),
    ("min", "lowest", re.compile(r"\b(lowest|minimum|min|sabse\s+kam|nyuntam)\b", re.IGNORECASE)),
    ("count", "how many", re.compile(r"\b(how\s+many|number\s+of|count\s+of|kitne|kitni|kitna|kul\s+sankhya)\b", re.IGNORECASE)),
    ("count", "count", re.compile(r"\b(count|headcount|sankhya)\b", re.IGNORECASE)),
    ("sum", "total", re.compile(r"\b(total|sum\s+of|sum|kul)\b", re.IGNORECASE)),
]

GROUP_BY_RE = re.compile(
    r"\b(?:per|by|each|every|har)\s+([a-zA-Z0-9_\-]+)",
    re.IGNORECASE
)

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "and", "or",
    "not", "have", "has", "had", "do", "does", "did", "can", "could", "shall",
    "should", "will", "would", "may", "might", "must", "there", "their", "this",
    "that", "these", "those", "it", "its", "as", "about", "into", "through",
    "after", "before", "between", "under", "above", "all", "any", "some", "such"
}

QUESTION_WORDS = {
    "who", "what", "where", "when", "why", "how", "which", "whom", "whose",
    "kya", "kaun", "kab", "kaha", "kahan", "kyu", "kyun", "kaise", "kitna", "kitne", "kitni",
    "kiska", "kiski", "kiske"
}

HINGLISH_FUNCTION_WORDS = {
    "mein", "me", "hain", "hai", "ka", "ki", "ke", "ko", "se", "ne", "par", "pe",
    "karein", "karna", "kare", "karta", "hoti", "hota", "hote", "bhi", "toh", "aur",
    "ya", "raha", "rahe", "rahi", "gaya", "gaye", "gayi"
}

GROUP_BY_WORDS = {"per", "by", "each", "every", "har"}

GENERAL_AGG_WORDS = {
    "count", "sum", "total", "average", "avg", "mean", "highest", "lowest",
    "maximum", "minimum", "max", "min", "kul", "sabse", "zyada", "jyada",
    "adhik", "adhiktam", "kam", "nyuntam", "ausat", "sankhya", "headcount",
    "number", "many"
}


# ── Core Feature Extractor ───────────────────────────────────────────────────

def extract_features(question: str, context: KBSchemaContext) -> QueryFeatures:
    """
    Extract pure QueryFeatures from question and schema context.
    Deterministic, rule-based, no LLM.
    """
    q_clean = question.strip()
    q_lower = q_clean.lower()

    # 1. Identifier Candidates & Hits
    # Candidates are tokens mixing ASCII letters and digits (e.g. E1007, INV-2024-001)
    raw_word_tokens = re.findall(r"\b[A-Za-z0-9_\-]+\b", q_clean)
    candidates: List[str] = []
    for tok in raw_word_tokens:
        has_letter = bool(re.search(r"[A-Za-z]", tok))
        has_digit = bool(re.search(r"[0-9]", tok))
        if has_letter and has_digit:
            candidates.append(tok)

    # Deduplicate candidates preserving order
    unique_candidates = list(dict.fromkeys(candidates))
    identifier_hits = list(context.resolve_identifiers(unique_candidates))

    # 2. Aggregation Intent
    agg_intent: Optional[AggregationIntent] = None
    for op, label, pat in AGGREGATION_PHRASES:
        m = pat.search(q_clean)
        if m:
            agg_intent = AggregationIntent(op=op, matched_phrase=m.group(0))
            break

    # 3. Row Identity Request ("who", "which", "kaun", "kiski")
    row_identity_request = bool(ROW_IDENTITY_RE.search(q_clean))

    # 4. Comparison Intent & Multi-Part
    comparison_intent = bool(COMPARISON_RE.search(q_clean))

    # Multi-part: 2+ ?, 2+ interrogatives, or > 25 words
    qmark_count = q_clean.count("?")
    interrogative_matches = re.findall(
        r"\b(" + "|".join(INTERROGATIVES) + r")\b",
        q_lower
    )
    word_count = len(q_clean.split())
    multi_part = (qmark_count >= 2) or (len(interrogative_matches) >= 2) or (word_count > 25)

    # 5. Column Mapping
    # Tokens to match against columns: words from question + lexical tokens
    q_tokens = list(dict.fromkeys(tokenize(q_clean) + [w.lower().strip("""!?,.:;()"'""") for w in q_clean.split()]))
    mapped_columns: List[ColumnMatch] = []
    seen_col_keys: Set[Tuple[int, str]] = set()

    for sid, table in context.tables.items():
        # Match table entity name (e.g. "employees" in employees_messy.csv)
        entity_name = _naive_stem(table.source_name.split(".")[0].split("_")[0])

        for col in table.columns:
            col_parts = _split_column_name(col)
            col_stems = [_naive_stem(p) for p in col_parts]
            full_col_stem = _naive_stem("".join(col_parts))
            role = table.column_roles.get(col, "category")

            matched_tok = None
            for q_tok in q_tokens:
                if len(q_tok) < 2:
                    continue
                q_stem = _naive_stem(q_tok)

                # Direct match with full column name or stem
                if q_stem == full_col_stem or q_tok == col.lower():
                    matched_tok = q_tok
                    break

                # Match any part of column name
                for c_stem in col_stems:
                    if q_stem == c_stem:
                        matched_tok = q_tok
                        break
                    # Edit distance <= 1 for length >= 5
                    if len(q_stem) >= 5 and len(c_stem) >= 5 and _levenshtein(q_stem, c_stem) <= 1:
                        matched_tok = q_tok
                        break

                if matched_tok:
                    break

            if matched_tok:
                key = (sid, col)
                if key not in seen_col_keys:
                    seen_col_keys.add(key)
                    mapped_columns.append(ColumnMatch(
                        column=col,
                        source_id=sid,
                        matched_token=matched_tok,
                        role=role,
                    ))

    # 6. Group By Hint ("per X", "by X", "each X", "every X", "har X")
    group_by_hint: Optional[str] = None
    m_grp = GROUP_BY_RE.search(q_clean)
    if m_grp:
        cand_grp = m_grp.group(1).lower().strip()
        cand_grp_stem = _naive_stem(cand_grp)
        # Check against category columns in structured tables
        for sid, table in context.tables.items():
            for col in table.columns:
                role = table.column_roles.get(col, "category")
                if role in ("category", "free_text", "optional"):
                    col_parts = _split_column_name(col)
                    col_stems = [_naive_stem(p) for p in col_parts]
                    if cand_grp == col.lower() or cand_grp_stem in col_stems:
                        group_by_hint = col
                        break
            if group_by_hint:
                break

    # 7. Filter Values (1-3 word category value matches)
    filter_values: List[FilterValueMatch] = []
    seen_filters: Set[Tuple[int, str, str]] = set()

    for sid, table in context.tables.items():
        for col, distinct_vals in table.category_values.items():
            for val in distinct_vals:
                v_clean = val.strip()
                if not v_clean or len(v_clean) < 2:
                    continue
                # Case-insensitive word boundary match
                pat = r"\b" + re.escape(v_clean) + r"\b"
                if re.search(pat, q_clean, re.IGNORECASE):
                    key = (sid, col, v_clean)
                    if key not in seen_filters:
                        seen_filters.add(key)
                        filter_values.append(FilterValueMatch(
                            column=col,
                            value=v_clean,
                            source_id=sid,
                        ))

    # Parse top_n
    top_n = 1
    m_top = re.search(r"\btop\s+(\d+)\b", q_clean, re.IGNORECASE)
    if m_top:
        top_n = min(max(int(m_top.group(1)), 1), 10)

    # 8. Mappability Assessment
    target_source_id: Optional[int] = None
    target_column: Optional[str] = None
    mappable = False
    mappable_reason = "no_aggregation_intent"
    unmapped_terms: List[str] = []

    # Must have exactly one structured source available or resolvable
    struct_sids = context.structured_source_ids
    if len(struct_sids) == 0:
        mappable_reason = "no_structured_sources"
    elif len(struct_sids) > 1:
        # Check if mapped columns or filters isolate exactly one source
        active_sids = set([c.source_id for c in mapped_columns] + [f.source_id for f in filter_values])
        if len(active_sids) == 1:
            target_source_id = next(iter(active_sids))
        else:
            mappable_reason = "multiple_structured_sources_unresolved"
    else:
        target_source_id = struct_sids[0]

    if target_source_id is not None:
        table_schema = context.tables[target_source_id]

        # 1. Collect accounted-for terms for this table
        # (a) Column name stems and parts
        col_stems = set()
        for col in table_schema.columns:
            col_stems.add(_naive_stem(col.lower()))
            for p in _split_column_name(col):
                col_stems.add(_naive_stem(p))

        # (b) Known category values stems
        cat_val_stems = set()
        for c, vals in table_schema.category_values.items():
            for v in vals:
                for part in re.findall(r"[a-zA-Z0-9]+", v.lower()):
                    cat_val_stems.add(_naive_stem(part))

        # (c) Entity noun of the table (stem of identifier column name, e.g. "employee")
        table_entity_stems = set()
        for id_c in table_schema.identifier_columns:
            for p in _split_column_name(id_c):
                p_s = _naive_stem(p)
                if p_s not in ("id", "code", "num", "number", "key", "uuid"):
                    table_entity_stems.add(p_s)
        src_stem = _naive_stem(table_schema.source_name.split(".")[0].split("_")[0])
        if src_stem:
            table_entity_stems.add(src_stem)
        if any("emp" in s for s in table_entity_stems):
            table_entity_stems.add("employee")

        # 2. Extract content words from question
        q_words = re.findall(r"[a-zA-Z0-9]+", q_lower)

        agg_phrase_words = set()
        if agg_intent:
            agg_phrase_words.update(re.findall(r"[a-zA-Z0-9]+", agg_intent.matched_phrase.lower()))

        for w in q_words:
            if (
                w in STOPWORDS
                or w in QUESTION_WORDS
                or w in HINGLISH_FUNCTION_WORDS
                or w in GROUP_BY_WORDS
                or w in GENERAL_AGG_WORDS
                or w in agg_phrase_words
                or (m_top and w in (str(top_n), "top"))
            ):
                continue

            w_stem = _naive_stem(w)

            # Check (a) column stem match
            matched_col = (w_stem in col_stems) or any(
                len(w_stem) >= 5 and len(cs) >= 5 and _levenshtein(w_stem, cs) <= 1
                for cs in col_stems
            )

            # Check (b) category value match
            matched_cat = (w_stem in cat_val_stems)

            # Check (c) entity noun match
            matched_entity = (w_stem in table_entity_stems)

            if not (matched_col or matched_cat or matched_entity):
                unmapped_terms.append(w)

        if agg_intent is not None:
            op = agg_intent.op

            # Filters validation
            all_filters_valid = True
            for f in filter_values:
                if f.source_id == target_source_id and f.column not in table_schema.category_values:
                    all_filters_valid = False
                    break

            # Group by validation
            grp_valid = True
            if group_by_hint:
                grp_role = table_schema.column_roles.get(group_by_hint, "")
                if grp_role not in ("category", "free_text", "optional") and group_by_hint not in table_schema.columns:
                    grp_valid = False

            # Always resolve target numeric column if op in sum/avg/min/max
            if op in ("sum", "avg", "min", "max"):
                numeric_matches = [
                    m for m in mapped_columns
                    if m.source_id == target_source_id and m.column in table_schema.numeric_columns
                ]
                if numeric_matches:
                    target_column = numeric_matches[0].column

            # Coverage check: if any content word is unmapped, CANNOT be structured!
            if unmapped_terms:
                mappable = False
                mappable_reason = f"unmapped_terms: {unmapped_terms}"
            elif not all_filters_valid:
                mappable = False
                mappable_reason = "filter_column_not_category"
            elif not grp_valid:
                mappable = False
                mappable_reason = "group_by_not_category_column"
            elif row_identity_request:
                if op in ("max", "min") and target_column:
                    mappable = True
                    mappable_reason = "mappable"
                else:
                    mappable = False
                    mappable_reason = "row_identity_not_supported"
            elif op in ("sum", "avg", "min", "max"):
                if target_column:
                    mappable = True
                    mappable_reason = "mappable"
                else:
                    mappable = False
                    mappable_reason = "no_numeric_column_for_op"
            elif op == "count":
                has_filters = any(f.source_id == target_source_id for f in filter_values)
                has_col_or_entity = any(m.source_id == target_source_id for m in mapped_columns)
                has_entity_in_q = any(_naive_stem(w) in table_entity_stems for w in q_lower.split())

                if has_filters or has_col_or_entity or has_entity_in_q or group_by_hint:
                    mappable = True
                    mappable_reason = "mappable"
                else:
                    mappable = False
                    mappable_reason = "count_missing_filter_or_entity"
        else:
            if row_identity_request:
                mappable = False
                mappable_reason = "row_identity_not_supported"

    return QueryFeatures(
        question=q_clean,
        identifier_candidates=unique_candidates,
        identifier_hits=identifier_hits,
        aggregation_intent=agg_intent,
        group_by_hint=group_by_hint,
        row_identity_request=row_identity_request,
        comparison_intent=comparison_intent,
        multi_part=multi_part,
        mapped_columns=mapped_columns,
        filter_values=filter_values,
        unmapped_terms=unmapped_terms,
        top_n=top_n,
        mappable=mappable,
        mappable_reason=mappable_reason,
        target_source_id=target_source_id,
        target_column=target_column,
    )
