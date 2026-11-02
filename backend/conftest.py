# conftest.py - project-wide pytest configuration for Sift backend.
# Ensures the project root is on sys.path for all tests.
# Enforces database isolation: all pytest runs must use TEST_DATABASE_URL (ending with _test).
# Redirects UPLOAD_DIR to a tmp_path so tests never write into the repo.

import os
import sys
import urllib.parse
from pathlib import Path
import pytest
from dotenv import load_dotenv

# Ensure backend directory is on sys.path and load environment variables from backend/.env
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

env_file = backend_dir / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv()

# ── Database Isolation ────────────────────────────────────────────────────────
# Default test database URL derived from configured DATABASE_URL
test_db_url = os.getenv("TEST_DATABASE_URL")
if not test_db_url:
    dev_url = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres@localhost:8887/ragstudio")
    parsed = urllib.parse.urlparse(dev_url)
    test_db_url = urllib.parse.urlunparse(parsed._replace(path="/ragstudio_test"))
    os.environ["TEST_DATABASE_URL"] = test_db_url

# Verify safety rule: test database must end with _test
parsed_test = urllib.parse.urlparse(test_db_url)
test_dbname = parsed_test.path.lstrip("/")
if not test_dbname.endswith("_test"):
    raise RuntimeError(
        f"Safety violation: TEST_DATABASE_URL database name '{test_dbname}' does not end with '_test'. "
        "Pytest refused to run against non-test database."
    )

# Force application code to point exclusively to the isolated test database during tests
os.environ["DATABASE_URL"] = test_db_url


@pytest.fixture(autouse=True)
def _isolate_upload_dir(tmp_path, monkeypatch):
    """
    Redirect UPLOAD_DIR to a per-test temp directory so no test files
    are written into the repo uploads/ folder.
    Applies to every test automatically (autouse=True).
    """
    import main as _main_mod
    test_uploads = tmp_path / "uploads"
    test_uploads.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(_main_mod, "UPLOAD_DIR", test_uploads)
    yield test_uploads
