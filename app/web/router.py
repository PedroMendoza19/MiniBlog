"""Front-end server-side (Jinja2). Lee de la base usando el mismo repository que la API.

Las escrituras (crear, editar, borrar) las hace el navegador contra la API JSON,
así el front no duplica validaciones: usa las mismas de Pydantic.
"""

import calendar
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.entries import repository
from app.api.v1.tags.router import language_counts, tag_counts
from app.core.db import get_db
from app.models import Difficulty, Entry

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

DB = Annotated[Session, Depends(get_db)]

MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MONTH_NAMES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]
WEEKDAYS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
DIFFICULTY_LABELS = {"beginner": "Básico", "intermediate": "Intermedio", "advanced": "Avanzado"}


# ---------- filtros de Jinja ----------

def fecha(value: date, with_year: bool = True) -> str:
    text = f"{value.day} {MONTHS[value.month - 1]}"
    return f"{text} {value.year}" if with_year else text


def render_text(value: str) -> Markup:
    """Texto plano -> HTML seguro: párrafos, saltos de línea, `código` y **negrita**."""
    html = str(escape(value))
    html = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", html)
    html = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", html)
    paragraphs = [p.strip().replace("\n", "<br>") for p in re.split(r"\n\s*\n", html) if p.strip()]
    return Markup("".join(f"<p>{p}</p>" for p in paragraphs))


def excerpt(value: str, length: int = 170) -> str:
    text = re.sub(r"[`*]", "", " ".join(value.split()))
    return text if len(text) <= length else text[:length].rsplit(" ", 1)[0] + "…"


def query_url(filters: dict, **changes) -> str:
    """URL de la home con los filtros actuales + cambios. Un valor None quita el filtro.
    Cambiar un filtro siempre vuelve a la página 1 (salvo que se pase page explícitamente)."""
    params = {**filters, "page": None, **changes}
    params = {k: v for k, v in params.items() if v not in (None, "") and not (k == "page" and v == 1)}
    return "/?" + urlencode(params) if params else "/"


def toggle_url(filters: dict, key: str, value: str) -> str:
    return query_url(filters, **{key: None if filters.get(key) == value else value})


templates.env.filters.update(fecha=fecha, render_text=render_text, excerpt=excerpt)
templates.env.globals.update(
    difficulty_labels=DIFFICULTY_LABELS, months=MONTHS, query_url=query_url, toggle_url=toggle_url
)


# ---------- helpers ----------

def activity(db: Session, weeks: int = 20, today: date | None = None) -> list[dict]:
    """Días para el heatmap estilo GitHub: arranca un lunes, termina hoy."""
    today = today or date.today()
    start = today - timedelta(days=today.weekday(), weeks=weeks - 1)
    counts = dict(
        db.execute(
            select(Entry.learned_on, func.count(Entry.id))
            .where(Entry.learned_on >= start)
            .group_by(Entry.learned_on)
        ).all()
    )
    days, current = [], start
    while current <= today:
        n = counts.get(current, 0)
        days.append({"date": current, "count": n, "level": min(n, 4)})
        current += timedelta(days=1)
    return days


def not_found(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "404.html", status_code=404)


# ---------- páginas ----------

@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    db: DB,
    q: Annotated[str | None, Query(max_length=100)] = None,
    tag: Annotated[str | None, Query(max_length=40)] = None,
    language: Annotated[str | None, Query(max_length=30)] = None,
    difficulty: Difficulty | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
):
    items, total, pages = repository.list_entries(
        db,
        page=page,
        size=8,
        q=q,
        tags=[tag] if tag else None,
        language=language,
        difficulty=difficulty,
    )
    filters = {
        k: v
        for k, v in {"q": q, "tag": tag, "language": language, "difficulty": difficulty and difficulty.value}.items()
        if v
    }
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "entries": items,
            "total": total,
            "page": page,
            "pages": pages,
            "filters": filters,
            "streak": repository.get_streak(db),
            "activity": activity(db),
            "tags": tag_counts(db)[:14],
            "languages": language_counts(db)[:8],
        },
    )


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


@router.get("/calendar", response_class=HTMLResponse)
def calendar_page(
    request: Request,
    db: DB,
    year: Annotated[int | None, Query(ge=2000, le=2100)] = None,
    month: Annotated[int | None, Query(ge=1, le=12)] = None,
):
    today = date.today()
    year, month = year or today.year, month or today.month

    # Semanas completas (lunes a domingo), incluyendo días del mes anterior/siguiente.
    weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
    entries = db.scalars(
        select(Entry)
        .where(Entry.learned_on.between(weeks[0][0], weeks[-1][-1]))
        .order_by(Entry.learned_on, Entry.id)
    )
    by_day: dict[date, list[Entry]] = defaultdict(list)
    for entry in entries:
        by_day[entry.learned_on].append(entry)

    in_month = [d for d in by_day if d.month == month]
    prev_year, prev_month = _shift_month(year, month, -1)
    next_year, next_month = _shift_month(year, month, 1)
    return templates.TemplateResponse(
        request,
        "calendar.html",
        {
            "year": year,
            "month": month,
            "month_name": MONTH_NAMES[month - 1],
            "weekdays": WEEKDAYS,
            "weeks": weeks,
            "by_day": by_day,
            "today": today,
            "month_total": sum(len(by_day[d]) for d in in_month),
            "month_active_days": len(in_month),
            "prev_url": f"/calendar?year={prev_year}&month={prev_month}",
            "next_url": f"/calendar?year={next_year}&month={next_month}",
            "is_current": (year, month) == (today.year, today.month),
        },
    )


@router.get("/random")
def random_page(db: DB):
    try:
        entry = repository.get_random(db)
    except repository.EntryNotFound:
        return RedirectResponse("/", status_code=303)
    return RedirectResponse(f"/e/{entry.slug}", status_code=303)


@router.get("/new", response_class=HTMLResponse)
def new_page(request: Request, db: DB):
    return templates.TemplateResponse(
        request,
        "form.html",
        {"entry": None, "today": date.today(), "languages": language_counts(db), "all_tags": tag_counts(db)},
    )


@router.get("/e/{slug}", response_class=HTMLResponse)
def entry_page(slug: str, request: Request, db: DB):
    try:
        entry = repository.get_by_slug(db, slug)
    except repository.EntryNotFound:
        return not_found(request)
    return templates.TemplateResponse(request, "entry.html", {"entry": entry})


@router.get("/e/{slug}/edit", response_class=HTMLResponse)
def edit_page(slug: str, request: Request, db: DB):
    try:
        entry = repository.get_by_slug(db, slug)
    except repository.EntryNotFound:
        return not_found(request)
    return templates.TemplateResponse(
        request,
        "form.html",
        {"entry": entry, "today": date.today(), "languages": language_counts(db), "all_tags": tag_counts(db)},
    )
