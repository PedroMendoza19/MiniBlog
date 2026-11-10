import os
import tempfile

# Antes de importar la app, así el engine "real" no toca devlog.db.
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.gettempdir()}/devlog_test_unused.db"
os.environ["ADMIN_KEY"] = ""  # los tests arrancan con escritura abierta; el fixture admin_key la activa

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, settings
from app.core.db import Base, get_db
from app.main import app


# Por defecto SQLite en memoria. Para probar contra Postgres:
#   TEST_DATABASE_URL=postgresql://user@localhost:5432/devlog_test pytest
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def _make_engine():
    if TEST_DATABASE_URL:
        return create_engine(Settings(database_url=TEST_DATABASE_URL).database_url)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


@pytest.fixture
def db_session():
    engine = _make_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def admin_key(monkeypatch):
    monkeypatch.setattr(settings, "admin_key", "s3cret")
    return "s3cret"


@pytest.fixture
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def make_entry(client):
    def _make(**overrides):
        payload = {
            "title": "Los walrus operators existen",
            "content": "Con := podés asignar dentro de una expresión.",
            "language": "python",
            "tags": ["python", "syntax"],
        }
        payload.update(overrides)
        res = client.post("/api/v1/entries", json=payload)
        assert res.status_code == 201, res.text
        return res.json()

    return _make
