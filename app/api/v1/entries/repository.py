import math
from datetime import date, timedelta

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.api.v1.entries.schemas import EntryCreate, EntryUpdate, SortField, SortOrder, StreakRead, TagMatch
from app.core.slug import slugify
from app.models import Difficulty, Entry, Tag, entry_tags


class EntryNotFound(Exception):
    pass


def _get_or_create_tags(db: Session, names: list[str]) -> list[Tag]:
    if not names:
        return []
    existing = {t.name: t for t in db.scalars(select(Tag).where(Tag.name.in_(names)))}
    tags = []
    for name in names:
        tag = existing.get(name)
        if tag is None:
            tag = Tag(name=name)
            db.add(tag)
        tags.append(tag)
    return tags


def _unique_slug(db: Session, title: str) -> str:
    base = slugify(title)
    taken = set(db.scalars(select(Entry.slug).where(Entry.slug.like(f"{base}%"))))
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def _apply_payload(db: Session, entry: Entry, data: EntryCreate | EntryUpdate) -> None:
    entry.title = data.title
    entry.content = data.content
    entry.code_snippet = data.code_snippet
    entry.language = data.language
    entry.difficulty = data.difficulty
    entry.reference_url = str(data.reference_url) if data.reference_url else None
    entry.learned_on = data.learned_on or date.today()
    entry.tags = _get_or_create_tags(db, data.tags)


def _filtered_query(
    q: str | None = None,
    tags: list[str] | None = None,
    tag_match: TagMatch = TagMatch.any,
    language: str | None = None,
    difficulty: Difficulty | None = None,
) -> Select:
    stmt = select(Entry)
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(Entry.title.ilike(pattern) | Entry.content.ilike(pattern))
    if language and language.strip():
        stmt = stmt.where(Entry.language == language.strip().lower())
    if difficulty:
        stmt = stmt.where(Entry.difficulty == difficulty)
    names = sorted({t.strip().lower() for t in (tags or []) if t.strip()})
    if names:
        matching = (
            select(entry_tags.c.entry_id)
            .join(Tag, Tag.id == entry_tags.c.tag_id)
            .where(Tag.name.in_(names))
            .group_by(entry_tags.c.entry_id)
        )
        if tag_match == TagMatch.all:
            matching = matching.having(func.count(func.distinct(Tag.id)) == len(names))
        stmt = stmt.where(Entry.id.in_(matching))
    return stmt


def list_entries(
    db: Session,
    *,
    page: int = 1,
    size: int = 10,
    sort: SortField = SortField.learned_on,
    order: SortOrder = SortOrder.desc,
    **filters,
) -> tuple[list[Entry], int, int]:
    stmt = _filtered_query(**filters)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    column = getattr(Entry, sort.value)
    if order == SortOrder.desc:
        ordering = (column.desc(), Entry.id.desc())
    else:
        ordering = (column.asc(), Entry.id.asc())
    items = list(db.scalars(stmt.order_by(*ordering).offset((page - 1) * size).limit(size)))
    pages = math.ceil(total / size) if total else 0
    return items, total, pages


def get_by_slug(db: Session, slug: str) -> Entry:
    entry = db.scalar(select(Entry).where(Entry.slug == slug))
    if entry is None:
        raise EntryNotFound(slug)
    return entry


def get_random(db: Session, **filters) -> Entry:
    entry = db.scalar(_filtered_query(**filters).order_by(func.random()).limit(1))
    if entry is None:
        raise EntryNotFound("random")
    return entry


def create_entry(db: Session, data: EntryCreate) -> Entry:
    entry = Entry(slug=_unique_slug(db, data.title))
    _apply_payload(db, entry, data)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def update_entry(db: Session, slug: str, data: EntryUpdate) -> Entry:
    # El slug no cambia al editar: así los links compartidos siguen funcionando.
    entry = get_by_slug(db, slug)
    _apply_payload(db, entry, data)
    db.commit()
    db.refresh(entry)
    return entry


def delete_entry(db: Session, slug: str) -> None:
    entry = get_by_slug(db, slug)
    db.delete(entry)
    db.commit()


def get_streak(db: Session, today: date | None = None) -> StreakRead:
    today = today or date.today()
    days = list(db.scalars(select(Entry.learned_on).distinct().order_by(Entry.learned_on.desc())))
    total = db.scalar(select(func.count(Entry.id))) or 0
    if not days:
        return StreakRead(current_streak=0, longest_streak=0, total_entries=0, active_days=0, last_entry_on=None)

    one_day = timedelta(days=1)

    # La racha actual sigue viva si la última entry es de hoy o de ayer.
    current = 0
    if today - days[0] <= one_day:
        current = 1
        for prev, curr in zip(days, days[1:]):
            if prev - curr != one_day:
                break
            current += 1

    longest = run = 1
    for prev, curr in zip(days, days[1:]):
        run = run + 1 if prev - curr == one_day else 1
        longest = max(longest, run)

    return StreakRead(
        current_streak=current,
        longest_streak=longest,
        total_entries=total,
        active_days=len(days),
        last_entry_on=days[0],
    )
