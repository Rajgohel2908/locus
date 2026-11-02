"""
scripts/reset_demo_db.py — Recreates a dedicated demo database.

Rules:
- The database name must end with '_demo', otherwise refuse and exit.
- Connects to PostgreSQL, terminates existing connections, drops and creates the demo database.
- Enables required extensions (vector, pg_trgm).
- Applies all migrations (002_phase2.sql through 006_phase6.sql) and nothing else.
"""

import os
import sys
import urllib.parse
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def get_demo_db_url() -> str:
    demo_url = os.getenv("DEMO_DATABASE_URL")
    if not demo_url:
        dev_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:raj1818@localhost:8887/ragstudio")
        parsed = urllib.parse.urlparse(dev_url)
        demo_url = urllib.parse.urlunparse(parsed._replace(path="/ragstudio_demo"))
    return demo_url


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


def reset_demo_database(demo_url: str = None) -> str:
    url = demo_url or get_demo_db_url()

    # Parse and validate database name
    parsed = urllib.parse.urlparse(url)
    db_name = parsed.path.lstrip("/")

    if not db_name.endswith("_demo"):
        print(f"[ERROR] Safety check failed: Demo database name must end with '_demo', got '{db_name}'. Refusing to reset.")
        sys.exit(1)

    host = parsed.hostname or "localhost"
    port = parsed.port or 8887
    user = parsed.username or "postgres"
    password = parsed.password or ""

    print(f"[RESET_DEMO] Connecting to PostgreSQL at {host}:{port} as user '{user}'...")
    conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    # Terminate existing connections to demo database
    print(f"[RESET_DEMO] Terminating any existing connections to database '{db_name}'...")
    cur.execute(
        """
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = %s AND pid <> pg_backend_pid();
        """,
        (db_name,),
    )

    # Drop and recreate demo database
    cur.execute(f"DROP DATABASE IF EXISTS {db_name};")
    print(f"[RESET_DEMO] Dropped database '{db_name}'.")
    cur.execute(f"CREATE DATABASE {db_name};")
    print(f"[RESET_DEMO] Created fresh database '{db_name}'.")

    cur.close()
    conn.close()

    # Connect to the fresh demo database and apply extensions & migrations
    demo_conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=db_name,
    )
    demo_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    demo_cur = demo_conn.cursor()

    print("[RESET_DEMO] Enabling extensions (vector, pg_trgm)...")
    try:
        demo_cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    except Exception as e:
        print(f"[WARN] vector extension warning: {e}")

    try:
        demo_cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    except Exception as e:
        print(f"[WARN] pg_trgm extension warning: {e}")

    demo_cur.close()
    demo_conn.close()

    # Create Phase 1 base tables via SQLAlchemy metadata
    print("[RESET_DEMO] Creating base ORM tables...")
    from sqlalchemy import create_engine
    backend_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(backend_dir))
    from db import Base
    demo_engine = create_engine(url)
    Base.metadata.create_all(bind=demo_engine)

    # Apply all migrations from backend/migrations
    demo_conn = psycopg2.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=db_name,
    )
    demo_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    demo_cur = demo_conn.cursor()

    migrations_dir = backend_dir / "migrations"
    migration_files = ["002_phase2.sql", "003_phase3.sql", "004_phase4.sql", "005_phase5.sql", "006_phase6.sql"]

    for fname in migration_files:
        mpath = migrations_dir / fname
        if mpath.exists():
            sql = mpath.read_text(encoding="utf-8-sig")
            for stmt in split_sql(sql):
                if stmt.strip():
                    try:
                        demo_cur.execute(stmt)
                    except Exception as e:
                        print(f"[WARN] Error executing statement in {fname}: {e}")
                        raise
            print(f"[RESET_DEMO] Applied migration: {fname}")
        else:
            print(f"[RESET_DEMO] Migration {fname} not found.")

    demo_cur.close()
    demo_conn.close()

    print(f"[OK] Demo database '{db_name}' ready with all migrations applied.")
    return url


if __name__ == "__main__":
    reset_demo_database()
