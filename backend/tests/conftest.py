import os

import pytest

# Minimal env so load_settings() succeeds in tests that need it.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("MQTT_HOST", "localhost")
os.environ.setdefault("MQTT_USERNAME", "u")
os.environ.setdefault("MQTT_PASSWORD", "p")
os.environ.setdefault("MQTT_USE_TLS", "false")
os.environ.setdefault("STORAGE_BACKEND", "disk")


@pytest.fixture
def settings():
    from app.config import load_settings

    return load_settings(exit_on_error=False)


@pytest.fixture
def db_session(tmp_path):
    """A SQLite-backed session factory with the schema created."""
    from app.db import session as session_mod
    from app.db.models import Base

    url = f"sqlite+pysqlite:///{tmp_path}/test.db"
    engine = session_mod.init_engine(url)
    Base.metadata.create_all(engine)
    return session_mod
