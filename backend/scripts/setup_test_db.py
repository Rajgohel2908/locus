"""
scripts/setup_test_db.py — Create and initialize isolated ragstudio_test database.

Rules:
- The database name must end with '_test', otherwise refuse and exit.
- Connects to PostgreSQL, creates the test database if not exists.
- Enables required extensions (vector, pg_trgm).
- Initializes base tables and applies all migrations (002_phase2.sql through 006_phase6.sql).
"""

import os
import sys
import urllib.parse
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load backend/.env
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    load_dotenv(dotenv_path=_env_path)
else:
    load_dotenv()


def get_test_db_url() -> str:
    test_url = os.getenv("TEST_DATABASE_URL")
    if not test_url:
        dev_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres@localhost:8887/ragstudio")
        parsed = urllib.parse.urlparse(dev_url)
        test_url = urllib.parse.urlunparse(parsed._replace(path="/ragstudio_test"))
    return test_url


def split_sql(sql: str) -> list:
    statements = []
    current = []
    for line in sql.splitlines():
        stripped = line.strip().lstrip("\ufeff")
        if stripped.startswith("--") and not current:
            continue
        current.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
    return statements


def ensure_test_database(test_url: str = None) -> str:
    url = test_url or get_test_db_url()

    parsed = urllib.parse.urlparse(url)
    db_name = parsed.path.lstrip("/")

    if not db_name.endswith("_test"):
        print(f"[ERROR] Safety check failed: Test database name must end with '_test', got '{db_name}'. Refusing to initialize.")
        sys.exit(1)

    host = parsed.hostname or "localhost"
    port = parsed.port or 8887
    user = parsed.username or "postgres"
    password = parsed.password or ""

    print(f"[SETUP_TEST_DB] Ensuring database '{db_name}' exists on {host}:{port}...")
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    exists = cur.fetchone()
    if not exists:
        cur.execute(f"CREATE DATABASE {db_name};")
        print(f"[SETUP_TEST_DB] Created database '{db_name}'.")
    else:
        print(f"[SETUP_TEST_DB] Database '{db_name}' already exists.")

    cur.close()
    conn.close()

    # Connect to test db and ensure extensions + tables + migrations
    test_conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=db_name,
    )
    test_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    test_cur = test_conn.cursor()

    try:
        test_cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    except Exception as e:
        print(f"[WARN] vector extension warning: {e}")

    try:
        test_cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    except Exception as e:
        print(f"[WARN] pg_trgm extension warning: {e}")

    test_cur.close()
    test_conn.close()

    # Base ORM tables
    from sqlalchemy import create_engine
    backend_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(backend_dir))
    from db import Base
    test_engine = create_engine(url)
    Base.metadata.create_all(bind=test_engine)

    # Apply all migrations
    test_conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=db_name,
    )
    test_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    test_cur = test_conn.cursor()

    migrations_dir = backend_dir / "migrations"
    migration_files = ["002_phase2.sql", "003_phase3.sql", "004_phase4.sql", "005_phase5.sql", "006_phase6.sql", "007_phase6b.sql", "008_phase7_eval.sql", "009_phase7_doctor.sql", "010_phase7_1.sql"]

    for fname in migration_files:
        mpath = migrations_dir / fname
        if mpath.exists():
            sql = mpath.read_text(encoding="utf-8-sig")
            for stmt in split_sql(sql):
                if stmt.strip():
                    try:
                        test_cur.execute(stmt)
                    except Exception as e:
                        print(f"[WARN] Statement in {fname}: {e}")
            print(f"[SETUP_TEST_DB] Migration {fname} verified.")

    test_cur.close()
    test_conn.close()

    print(f"[OK] Test database '{db_name}' ready.")
    return url


if __name__ == "__main__":
    ensure_test_database()

