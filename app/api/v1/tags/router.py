from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models import Entry, Tag, entry_tags

router = APIRouter(tags=["tags"])


class TagCount(BaseModel):
    name: str
    count: int


class LanguageCount(BaseModel):
    name: str
    count: int


def tag_counts(db: Session) -> list[TagCount]:
    rows = db.execute(
        select(Tag.name, func.count(entry_tags.c.entry_id).label("count"))
        .join(entry_tags, entry_tags.c.tag_id == Tag.id)
        .group_by(Tag.id)
        .order_by(func.count(entry_tags.c.entry_id).desc(), Tag.name)
    )
    return [TagCount(name=name, count=count) for name, count in rows]


def language_counts(db: Session) -> list[LanguageCount]:
    rows = db.execute(
        select(Entry.language, func.count(Entry.id))
        .where(Entry.language.is_not(None))
        .group_by(Entry.language)
        .order_by(func.count(Entry.id).desc(), Entry.language)
    )
    return [LanguageCount(name=name, count=count) for name, count in rows]


@router.get("/tags", response_model=list[TagCount], summary="Tags en uso, con cantidad de entries")
def list_tags(db: Annotated[Session, Depends(get_db)]):
    return tag_counts(db)


@router.get("/languages", response_model=list[LanguageCount], summary="Lenguajes usados, con cantidad de entries")
def list_languages(db: Annotated[Session, Depends(get_db)]):
    return language_counts(db)
