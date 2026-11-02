"""
tests/test_phase6a_routing.py — Table-driven tests for Phase 6A query analyzer and router.

Covers:
- English and Hinglish query feature extraction
- Rule priority: structured -> exact -> complex -> semantic
- Router coverage rule: unmapped terms must cause fallback to semantic RAG
- All must-pass cases with the real messy employees CSV schema in scope:
  Negatives (unmapped content words -> semantic):
    1. "How many annual leaves are employees entitled to?" -> semantic (unmapped_terms: ['annual', 'leaves', 'entitled'])
    2. "How many days of sick leave do employees get?" -> semantic (unmapped_terms: ['days', 'sick', 'leave', 'get'])
    3. "What is the total working hours per week?" -> semantic (unmapped_terms: ['working', 'hours', 'week'])
  Positives (all content words mapped -> structured):
    4. "How many employees are in each department?" -> structured count group_by Department
    5. "What is the average salary in Mumbai?" -> structured avg Salary filter City=Mumbai
    6. "Mumbai mein kitne employees hain?" -> structured count filter City=Mumbai
    7. "What is the total salary of employees in Finance?" -> structured sum Salary filter Department=Finance
- Row identity routing:
    8. "Who has the highest salary?" -> structured (template top_n, op max, col Salary)
    9. "Who has the highest bonus?" -> semantic fallback / insufficient evidence (bonus unmapped)
- Cross-encoder unavailable fallback: fallback to hybrid with recorded note
- Rules version assertion (router-rules-v1) and fired/rejected rule audit trails
"""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base, Source, Record
from routing.context import KBSchemaContext, StructuredTableSchema, build_schema_context
from routing.features import extract_features
from routing.router import decide_route, ROUTER_RULES_VERSION


@pytest.fixture
def fake_schema_context():
    """
    Fixed fake schema context with the real schema of the messy employees CSV in scope:
    Columns: Employee_ID, Name, Department, Salary, Joining_Date, Manager, City
    """
    emp_table = StructuredTableSchema(
        source_id=1,
        source_name="employees_messy.csv",
        version=2,
        columns=["Employee_ID", "Name", "Department", "Salary", "Joining_Date", "Manager", "City"],
        column_roles={
            "Employee_ID": "identifier",
            "Name": "free_text",
            "Department": "category",
            "Salary": "numeric",
            "Joining_Date": "date",
            "Manager": "category",
            "City": "category",
        },
        dtypes={
            "Employee_ID": "object",
            "Name": "object",
            "Department": "object",
            "Salary": "float64",
            "Joining_Date": "object",
            "Manager": "object",
            "City": "object",
        },
        category_values={
            "Department": ["Operations", "Marketing", "HR", "Finance", "Sales", "Engineering"],
            "City": ["Mumbai", "Pune", "Delhi", "Chennai", "Hyderabad", "Bangalore"],
            "Manager": ["Manager_2", "Manager_3", "Manager_4", "Manager_5", "Manager_14"],
        },
        identifier_columns=["Employee_ID"],
        numeric_columns=["Salary"],
    )

    known_ids = {"e1007", "e0001", "e0002", "inv-2024-001"}

    def fake_resolver(tokens):
        return {t.lower().strip() for t in tokens if t.lower().strip() in known_ids}

    return KBSchemaContext(
        tables={1: emp_table},
        all_source_ids=[1, 2],
        custom_identifier_resolver=fake_resolver,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Must-Pass Cases Table-Driven Test
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "question, expected_route, expected_strategy, expected_op, expected_col, expected_filter_col, expected_filter_val, expected_grp",
    [
        # Negative 1: Annual leaves -> unmapped terms -> semantic
        (
            "How many annual leaves are employees entitled to?",
            "semantic",
            "hybrid",
            "count",
            None,
            None,
            None,
            None,
        ),
        # Negative 2: Sick leave -> unmapped terms -> semantic
        (
            "How many days of sick leave do employees get?",
            "semantic",
            "hybrid",
            "count",
            None,
            None,
            None,
            None,
        ),
        # Negative 3: Working hours per week -> unmapped terms -> semantic
        (
            "What is the total working hours per week?",
            "semantic",
            "hybrid",
            "sum",
            None,
            None,
            None,
            None,
        ),
        # Positive 1: Structured average with filter
        (
            "What is the average salary in Mumbai?",
            "structured",
            "structured",
            "avg",
            "Salary",
            "City",
            "Mumbai",
            None,
        ),
        # Positive 2: Structured count with group_by
        (
            "How many employees are in each department?",
            "structured",
            "structured",
            "count",
            None,
            None,
            None,
            "Department",
        ),
        # Positive 3: Hinglish structured count with filter
        (
            "Mumbai mein kitne employees hain?",
            "structured",
            "structured",
            "count",
            None,
            "City",
            "Mumbai",
            None,
        ),
        # Positive 4: Total salary in Finance
        (
            "What is the total salary of employees in Finance?",
            "structured",
            "structured",
            "sum",
            "Salary",
            "Department",
            "Finance",
            None,
        ),
        # Exact identifier query
        (
            "What is employee E1007's department?",
            "exact",
            "hybrid",
            None,
            None,
            None,
            None,
            None,
        ),
        # Complex comparison query
        (
            "Compare the 2019 and 2024 leave policies",
            "complex",
            "hybrid_rerank",
            None,
            None,
            None,
            None,
            None,
        ),
        # Row identity query on mapped numeric column -> structured top_n
        (
            "Who has the highest salary?",
            "structured",
            "structured",
            "max",
            "Salary",
            None,
            None,
            None,
        ),
        # Unsupported out-of-domain question
        (
            "What is the company's Mars colonization budget?",
            "semantic",
            "hybrid",
            None,
            None,
            None,
            None,
            None,
        ),
    ]
)
def test_must_pass_routing_cases(
    fake_schema_context,
    question,
    expected_route,
    expected_strategy,
    expected_op,
    expected_col,
    expected_filter_col,
    expected_filter_val,
    expected_grp,
):
    features = extract_features(question, fake_schema_context)
    decision = decide_route(features)

    assert decision.route == expected_route
    assert decision.strategy == expected_strategy
    assert decision.rules_version == ROUTER_RULES_VERSION

    if expected_op:
        assert features.aggregation_intent is not None
        assert features.aggregation_intent.op == expected_op

    if expected_col:
        assert features.target_column == expected_col

    if expected_filter_col:
        matched = any(f.column == expected_filter_col and f.value == expected_filter_val for f in features.filter_values)
        assert matched, f"Expected filter ({expected_filter_col}, {expected_filter_val}) not found in {features.filter_values}"

    if expected_grp:
        assert features.group_by_hint == expected_grp


# ─────────────────────────────────────────────────────────────────────────────
# 2. Detailed Coverage Rule and Unmapped Terms Audit
# ─────────────────────────────────────────────────────────────────────────────

def test_unmapped_terms_audit_records_reasons(fake_schema_context):
    f1 = extract_features("How many annual leaves are employees entitled to?", fake_schema_context)
    assert not f1.mappable
    assert "annual" in f1.unmapped_terms
    assert "leaves" in f1.unmapped_terms or "entitled" in f1.unmapped_terms
    assert f1.mappable_reason.startswith("unmapped_terms:")

    dec1 = decide_route(f1)
    assert dec1.route == "semantic"
    assert any("rule_structured_rejected: unmapped_terms" in r for r in dec1.reasons)

    f2 = extract_features("What is the total working hours per week?", fake_schema_context)
    assert not f2.mappable
    assert "working" in f2.unmapped_terms
    assert "hours" in f2.unmapped_terms or "week" in f2.unmapped_terms
    dec2 = decide_route(f2)
    assert dec2.route == "semantic"


def test_row_identity_mapped_and_unmapped(fake_schema_context):
    # Mapped row identity -> structured
    f_mapped = extract_features("Who has the highest salary?", fake_schema_context)
    assert f_mapped.row_identity_request is True
    assert f_mapped.target_column == "Salary"
    assert f_mapped.mappable is True
    dec_mapped = decide_route(f_mapped)
    assert dec_mapped.route == "structured"
    assert any("template='top_n'" in r for r in dec_mapped.reasons)

    # Top N parsing
    f_top3 = extract_features("Who are the top 3 highest salary employees?", fake_schema_context)
    assert f_top3.top_n == 3
    assert f_top3.mappable is True
    dec_top3 = decide_route(f_top3)
    assert dec_top3.route == "structured"

    # Unmapped row identity (e.g. bonus is not a column)
    f_unmapped = extract_features("Who has the highest bonus?", fake_schema_context)
    assert f_unmapped.row_identity_request is True
    assert not f_unmapped.mappable
    assert "bonus" in f_unmapped.unmapped_terms
    dec_unmapped = decide_route(f_unmapped)
    assert dec_unmapped.route == "semantic"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Cross-Encoder Availability Fallback Test
# ─────────────────────────────────────────────────────────────────────────────

def test_complex_route_cross_encoder_fallback(fake_schema_context):
    q = "Compare the 2019 and 2024 leave policies"
    features = extract_features(q, fake_schema_context)
    assert features.comparison_intent is True

    # When cross-encoder is available
    dec_available = decide_route(features, availability={"cross_encoder_available": True})
    assert dec_available.route == "complex"
    assert dec_available.strategy == "hybrid_rerank"
    assert len(dec_available.fallbacks) == 0

    # When cross-encoder is NOT available
    dec_unavailable = decide_route(features, availability={"cross_encoder_available": False})
    assert dec_unavailable.route == "complex"
    assert dec_unavailable.strategy == "hybrid"
    assert any("cross_encoder_unavailable" in f for f in dec_unavailable.fallbacks)


# ─────────────────────────────────────────────────────────────────────────────
# 4. Hinglish Keywords Feature Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_hinglish_keywords(fake_schema_context):
    f1 = extract_features("Operations mein kitne employees hain?", fake_schema_context)
    assert f1.aggregation_intent is not None
    assert f1.aggregation_intent.op == "count"
    assert any(f.column == "Department" and f.value == "Operations" for f in f1.filter_values)
    assert f1.mappable is True

    f2 = extract_features("Engineering department ka ausat salary kitna hai?", fake_schema_context)
    assert f2.aggregation_intent is not None
    assert f2.aggregation_intent.op == "avg"
    assert f2.target_column == "Salary"

    f3 = extract_features("Operations department mein sabse zyada salary kya hai?", fake_schema_context)
    assert f3.aggregation_intent is not None
    assert f3.aggregation_intent.op == "max"
    assert f3.target_column == "Salary"

    f4 = extract_features("Mumbai mein sabse kam salary kitni hai?", fake_schema_context)
    assert f4.aggregation_intent is not None
    assert f4.aggregation_intent.op == "min"
    assert f4.target_column == "Salary"

    f5 = extract_features("Har department mein kitne employees hain?", fake_schema_context)
    assert f5.group_by_hint == "Department"
    assert f5.mappable is True


# ─────────────────────────────────────────────────────────────────────────────
# 5. PostgreSQL Schema Context Integration Test (requires real PG database)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.pg
def test_schema_context_against_pg():
    import urllib.parse
    db_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL", "")
    if not (db_url.startswith("postgresql://") or db_url.startswith("postgresql+")):
        pytest.fail(f"TEST_DATABASE_URL must be a real PostgreSQL database, got: '{db_url}'")

    parsed = urllib.parse.urlparse(db_url)
    db_name = parsed.path.lstrip("/")
    if not db_name.endswith("_test"):
        pytest.fail(f"Safety check failed: pg test database name must end with '_test', got '{db_name}'. Refusing to run tests against non-test database.")

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create a test structured source and active records
        src = Source(source_type="file", name="pg_routing_test.csv")
        session.add(src)
        session.commit()

        recs = [
            Record(source_id=src.id, row_index=1, version_no=1, status="active", data={"EmpID": "E9001", "City": "Mumbai", "Salary": "50000"}),
            Record(source_id=src.id, row_index=2, version_no=1, status="active", data={"EmpID": "E9002", "City": "Delhi", "Salary": "60000"}),
        ]
        session.add_all(recs)
        session.commit()

        ctx = build_schema_context(db=session, source_ids=[src.id], version=1)
        assert src.id in ctx.tables
        table = ctx.tables[src.id]
        assert "Salary" in table.columns
        assert "City" in table.columns

        # Verify SQL-bound identifier lookup on PostgreSQL
        hits = ctx.resolve_identifiers(["E9001", "E9999"])
        assert "e9001" in {h.lower() for h in hits}
        assert "e9999" not in {h.lower() for h in hits}

    finally:
        session.query(Record).filter(Record.source_id == src.id).delete()
        session.delete(src)
        session.commit()
        session.close()
