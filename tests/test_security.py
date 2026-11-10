from app.core.config import Settings

API = "/api/v1/entries"
PAYLOAD = {"title": "Una entry", "content": "Contenido"}


def test_database_url_gets_psycopg_driver():
    assert Settings(database_url="postgres://u:p@host/db").database_url == "postgresql+psycopg://u:p@host/db"
    assert (
        Settings(database_url="postgresql://u:p@host/db?sslmode=require").database_url
        == "postgresql+psycopg://u:p@host/db?sslmode=require"
    )
    assert Settings(database_url="sqlite:///./x.db").database_url == "sqlite:///./x.db"


def test_empty_admin_key_means_open():
    assert Settings(admin_key="  ").admin_key is None


def test_writes_open_without_admin_key(client):
    assert client.post(API, json=PAYLOAD).status_code == 201
    assert client.get("/api/v1/admin/check").json() == {"ok": True, "protected": False}


def test_writes_require_admin_key(client, admin_key):
    assert client.post(API, json=PAYLOAD).status_code == 401
    assert client.post(API, json=PAYLOAD, headers={"X-Admin-Key": "mal"}).status_code == 401

    ok = {"X-Admin-Key": admin_key}
    slug = client.post(API, json=PAYLOAD, headers=ok).json()["slug"]

    # Leer sigue siendo público
    assert client.get(f"{API}/{slug}").status_code == 200
    assert client.get(API).json()["total"] == 1
    assert client.get("/").status_code == 200

    assert client.put(f"{API}/{slug}", json=PAYLOAD).status_code == 401
    assert client.put(f"{API}/{slug}", json=PAYLOAD, headers=ok).status_code == 200
    assert client.delete(f"{API}/{slug}").status_code == 401
    assert client.delete(f"{API}/{slug}", headers=ok).status_code == 204

    assert client.get("/api/v1/admin/check").status_code == 401
    assert client.get("/api/v1/admin/check", headers=ok).json() == {"ok": True, "protected": True}
