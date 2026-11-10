from app.web.router import query_url, render_text, toggle_url


def test_render_text_is_safe_and_formats():
    html = render_text("Usá `x := 1` y **listo**.\n\n<script>alert(1)</script>")
    assert "<code>x := 1</code>" in html
    assert "<strong>listo</strong>" in html
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert html.count("<p>") == 2


def test_query_url_helpers():
    filters = {"q": "async", "tag": "python"}
    assert query_url(filters) == "/?q=async&tag=python"
    assert query_url(filters, page=2) == "/?q=async&tag=python&page=2"
    assert toggle_url(filters, "tag", "python") == "/?q=async"  # desactiva
    assert toggle_url(filters, "tag", "sql") == "/?q=async&tag=sql"
    assert query_url({}) == "/"


def test_pages_render(client, make_entry):
    assert "Tu dev log está vacío" in client.get("/").text

    entry = make_entry(title="Generators en Python", code_snippet="def gen():\n    yield 1",
                       reference_url="https://docs.python.org/3/")
    home = client.get("/")
    assert home.status_code == 200
    assert "Generators en Python" in home.text
    assert "#python" in home.text

    page = client.get(f"/e/{entry['slug']}")
    assert page.status_code == 200
    assert "language-python" in page.text
    assert "https://docs.python.org/3/" in page.text

    assert client.get(f"/e/{entry['slug']}/edit").status_code == 200
    assert client.get("/new").status_code == 200
    assert client.get("/e/no-existe").status_code == 404

    res = client.get("/random", follow_redirects=False)
    assert res.status_code == 303 and res.headers["location"] == f"/e/{entry['slug']}"


def test_calendar(client, make_entry):
    from datetime import date

    from app.web.router import _shift_month

    assert _shift_month(2026, 1, -1) == (2025, 12)
    assert _shift_month(2026, 12, 1) == (2027, 1)

    today = date.today()
    make_entry(title="Entry de este mes")
    make_entry(title="Entry vieja", learned_on="2025-03-15")

    page = client.get("/calendar")
    assert page.status_code == 200
    assert "Entry de este mes" in page.text and "Entry vieja" not in page.text
    assert "is-today" in page.text

    page = client.get("/calendar", params={"year": 2025, "month": 3})
    assert "Marzo" in page.text and "Entry vieja" in page.text
    assert "Entry de este mes" not in page.text or (today.year, today.month) == (2025, 3)
    assert 'href="/calendar?year=2025&amp;month=2"' in page.text
    assert 'href="/calendar?year=2025&amp;month=4"' in page.text

    assert client.get("/calendar", params={"month": 13}).status_code == 422

    # El link "Calendario" funciona como toggle: desde el calendario vuelve al home.
    import re

    def nav_link(html):
        return " ".join(re.search(r'<a class="nav__link[^>]*title="[^"]*"', html, re.S).group(0).split())

    on_calendar = nav_link(client.get("/calendar").text)
    assert 'is-active' in on_calendar and 'href="/"' in on_calendar and "Volver al inicio" in on_calendar
    on_home = nav_link(client.get("/").text)
    assert 'is-active' not in on_home and 'href="/calendar"' in on_home
    assert "← Volver al inicio" in client.get("/calendar").text


def test_home_filters(client, make_entry):
    make_entry(title="Entry de SQL", language="sql", tags=["sql"])
    make_entry(title="Entry de Python", language="python", tags=["python"])
    text = client.get("/", params={"tag": "sql"}).text
    assert "Entry de SQL" in text and "Entry de Python" not in text
    assert "1</strong> resultado" in text
