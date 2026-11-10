from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.entries import repository
from app.api.v1.entries.schemas import (
    EntryCreate,
    EntryPage,
    EntryRead,
    EntryUpdate,
    SortField,
    SortOrder,
    StreakRead,
    TagMatch,
)
from app.core.db import get_db
from app.models import Difficulty

router = APIRouter(prefix="/entries", tags=["entries"])

DB = Annotated[Session, Depends(get_db)]


class EntryFilters:
    """Filtros compartidos entre el listado y /random."""

    def __init__(
        self,
        q: Annotated[str | None, Query(max_length=100, description="Busca en título y contenido")] = None,
        tags: Annotated[list[str] | None, Query(description="Uno o más tags (?tags=python&tags=sql)")] = None,
        tag_match: Annotated[TagMatch, Query(description="'any': alguno de los tags, 'all': todos")] = TagMatch.any,
        language: Annotated[str | None, Query(max_length=30)] = None,
        difficulty: Difficulty | None = None,
    ):
        self.q = q
        self.tags = tags
        self.tag_match = tag_match
        self.language = language
        self.difficulty = difficulty

    def as_dict(self) -> dict:
        return vars(self)


Filters = Annotated[EntryFilters, Depends()]


def _not_found(slug: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail=f"No existe la entry '{slug}'")


def _persistence_error() -> HTTPException:
    return HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al guardar en la base de datos")


@router.get("", response_model=EntryPage, summary="Listar entries")
def list_entries(
    db: DB,
    filters: Filters,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 10,
    sort: SortField = SortField.learned_on,
    order: SortOrder = SortOrder.desc,
):
    items, total, pages = repository.list_entries(
        db, page=page, size=size, sort=sort, order=order, **filters.as_dict()
    )
    return EntryPage(
        items=[EntryRead.model_validate(e) for e in items], total=total, page=page, size=size, pages=pages
    )


@router.get("/random", response_model=EntryRead, summary="Una entry al azar (para repasar)")
def random_entry(db: DB, filters: Filters):
    try:
        return repository.get_random(db, **filters.as_dict())
    except repository.EntryNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No hay entries que coincidan")


@router.get("/streak", response_model=StreakRead, summary="Racha de días seguidos aprendiendo")
def streak(db: DB):
    return repository.get_streak(db)


@router.get("/{slug}", response_model=EntryRead, response_model_exclude_none=False, summary="Ver una entry")
def get_entry(slug: str, db: DB):
    try:
        return repository.get_by_slug(db, slug)
    except repository.EntryNotFound:
        raise _not_found(slug)


@router.post("", response_model=EntryRead, status_code=status.HTTP_201_CREATED, summary="Crear una entry")
def create_entry(data: EntryCreate, db: DB):
    try:
        return repository.create_entry(db, data)
    except SQLAlchemyError:
        db.rollback()
        raise _persistence_error()


@router.put("/{slug}", response_model=EntryRead, summary="Editar una entry")
def update_entry(slug: str, data: EntryUpdate, db: DB):
    try:
        return repository.update_entry(db, slug, data)
    except repository.EntryNotFound:
        raise _not_found(slug)
    except SQLAlchemyError:
        db.rollback()
        raise _persistence_error()


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT, summary="Borrar una entry")
def delete_entry(slug: str, db: DB):
    try:
        repository.delete_entry(db, slug)
    except repository.EntryNotFound:
        raise _not_found(slug)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
