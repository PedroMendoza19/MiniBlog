from datetime import date, timedelta

from app.api.v1.entries.repository import get_streak
from app.api.v1.entries.schemas import EntryCreate
from app.api.v1.entries import repository
from app.core.slug import slugify

API = "/api/v1/entries"


def test_slugify_removes_accents_and_symbols():
    assert slugify("¿Qué es un decorador?") == "que-es-un-decorador"
    assert slugify("   !!!  ") == "entry"


def test_create_entry_generates_slug_and_normalizes(make_entry):
    entry = make_entry(title="  Async en Python  ", language=" Python ", tags=["Python", "python", " async "])
    assert entry["slug"] == "async-en-python"
    assert entry["title"] == "Async en Python"
    assert entry["language"] == "python"
    assert entry["tags"] == ["async", "python"]
    assert entry["learned_on"] == date.today().isoformat()
    assert entry["difficulty"] == "beginner"


def test_duplicate_titles_get_unique_slugs(make_entry):
    assert make_entry(title="Git rebase")["slug"] == "git-rebase"
    assert make_entry(title="Git rebase")["slug"] == "git-rebase-2"
    assert make_entry(title="Git rebase!")["slug"] == "git-rebase-3"


def test_validation_errors(client):
    future = (date.today() + timedelta(days=1)).isoformat()
    cases = [
        {"title": "ab", "content": "x"},
        {"title": "Título ok", "content": "   "},
        {"title": "Título ok", "content": "x", "learned_on": future},
        {"title": "Título ok", "content": "x", "reference_url": "no-es-una-url"},
        {"title": "Título ok", "content": "x", "difficulty": "godlike"},
        {"title": "Título ok", "content": "x", "tags": [f"t{i}" for i in range(11)]},
    ]
    for payload in cases:
        assert client.post(API, json=payload).status_code == 422, payload


def test_get_update_delete(client, make_entry):
    slug = make_entry(title="CTEs en SQL", language="sql", tags=["sql"])["slug"]

    res = client.get(f"{API}/{slug}")
    assert res.status_code == 200
    assert res.json()["title"] == "CTEs en SQL"

    res = client.put(
        f"{API}/{slug}",
        json={"title": "CTEs recursivas en SQL", "content": "WITH RECURSIVE ...", "tags": ["sql", "postgres"],
              "difficulty": "advanced"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["slug"] == slug  # el slug no cambia al editar
    assert body["title"] == "CTEs recursivas en SQL"
    assert body["tags"] == ["postgres", "sql"]
    assert body["difficulty"] == "advanced"

    assert client.delete(f"{API}/{slug}").status_code == 204
    assert client.get(f"{API}/{slug}").status_code == 404
    assert client.delete(f"{API}/{slug}").status_code == 404
    assert client.put(f"{API}/{slug}", json={"title": "Algo", "content": "x"}).status_code == 404


def test_list_pagination_and_sorting(client, make_entry):
    for i, title in enumerate(["Bravo", "Alpha", "Charlie"]):
        make_entry(title=title, learned_on=(date.today() - timedelta(days=i)).isoformat())

    res = client.get(API, params={"size": 2})
    body = res.json()
    assert body["total"] == 3 and body["pages"] == 2 and body["page"] == 1
    assert [e["title"] for e in body["items"]] == ["Bravo", "Alpha"]  # más reciente primero

    res = client.get(API, params={"size": 2, "page": 2})
    assert [e["title"] for e in res.json()["items"]] == ["Charlie"]

    res = client.get(API, params={"sort": "title", "order": "asc"})
    assert [e["title"] for e in res.json()["items"]] == ["Alpha", "Bravo", "Charlie"]

    assert client.get(API, params={"size": 51}).status_code == 422


def test_filters(client, make_entry):
    make_entry(title="Generators", language="python", tags=["python", "iterators"], difficulty="intermediate")
    make_entry(title="Window functions", content="ROW_NUMBER() OVER", language="sql", tags=["sql"])
    make_entry(title="Docker multi-stage", language="dockerfile", tags=["docker", "python"])

    def titles(**params):
        return sorted(e["title"] for e in client.get(API, params=params).json()["items"])

    assert titles(q="window") == ["Window functions"]
    assert titles(q="row_number") == ["Window functions"]  # busca también en el contenido
    assert titles(language="SQL") == ["Window functions"]
    assert titles(difficulty="intermediate") == ["Generators"]
    assert titles(tags=["python"]) == ["Docker multi-stage", "Generators"]
    assert titles(tags=["sql", "docker"]) == ["Docker multi-stage", "Window functions"]
    assert titles(tags=["python", "docker"], tag_match="all") == ["Docker multi-stage"]
    assert titles(tags=["nada"]) == []


def test_random(client, make_entry):
    assert client.get(f"{API}/random").status_code == 404
    make_entry(title="Solo python", tags=["python"])
    make_entry(title="Solo sql", tags=["sql"])
    for _ in range(5):
        assert client.get(f"{API}/random", params={"tags": "sql"}).json()["title"] == "Solo sql"


def test_streak_endpoint_empty(client):
    assert client.get(f"{API}/streak").json() == {
        "current_streak": 0, "longest_streak": 0, "total_entries": 0, "active_days": 0, "last_entry_on": None,
    }


def _add(db, days_ago: int, today: date):
    repository.create_entry(
        db, EntryCreate(title=f"Entry {days_ago}", content="x", learned_on=today - timedelta(days=days_ago))
    )


def test_streak_logic(db_session):
    today = date.today()
    # Hoy, ayer, anteayer (racha de 3) + dos entries el mismo día hace 10 y 11 días (racha de 2).
    for days_ago in [0, 1, 2, 10, 10, 11]:
        _add(db_session, days_ago, today)

    streak = get_streak(db_session, today=today)
    assert streak.current_streak == 3
    assert streak.longest_streak == 3
    assert streak.total_entries == 6
    assert streak.active_days == 5

    # Si hoy todavía no escribiste, la racha sigue viva desde ayer...
    assert get_streak(db_session, today=today + timedelta(days=1)).current_streak == 3
    # ...pero se corta si pasaron dos días.
    assert get_streak(db_session, today=today + timedelta(days=2)).current_streak == 0


def test_tags_and_languages(client, make_entry):
    make_entry(title="Uno", language="python", tags=["python", "async"])
    make_entry(title="Dos", language="python", tags=["python"])
    make_entry(title="Tres", language="sql", tags=["sql"])

    assert client.get("/api/v1/tags").json() == [
        {"name": "python", "count": 2}, {"name": "async", "count": 1}, {"name": "sql", "count": 1},
    ]
    assert client.get("/api/v1/languages").json() == [
        {"name": "python", "count": 2}, {"name": "sql", "count": 1},
    ]
