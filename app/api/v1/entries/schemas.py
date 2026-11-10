from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.models.entry import Difficulty


def _normalize_tags(tags: list[str]) -> list[str]:
    seen: list[str] = []
    for tag in tags:
        name = tag.strip().lower()
        if not name:
            continue
        if len(name) > 40:
            raise ValueError(f"El tag '{name}' supera los 40 caracteres")
        if name not in seen:
            seen.append(name)
    if len(seen) > 10:
        raise ValueError("Una entry no puede tener más de 10 tags")
    return seen


class EntryBase(BaseModel):
    title: str = Field(min_length=3, max_length=120, examples=["Los walrus operators existen"])
    content: str = Field(min_length=1, examples=["Con `:=` podés asignar dentro de una expresión."])
    code_snippet: str | None = Field(default=None, examples=["if (n := len(items)) > 10:\n    print(n)"])
    language: str | None = Field(default=None, max_length=30, examples=["python"])
    difficulty: Difficulty = Difficulty.beginner
    reference_url: HttpUrl | None = None
    learned_on: date | None = Field(default=None, description="Día en que lo aprendiste (por defecto, hoy)")
    tags: list[str] = Field(default_factory=list, examples=[["python", "syntax"]])

    @field_validator("title", "content")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("No puede estar vacío")
        return value.strip()

    @field_validator("code_snippet", "language", mode="before")
    @classmethod
    def empty_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str | None) -> str | None:
        return value.strip().lower() if value else None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return _normalize_tags(value)

    @field_validator("learned_on")
    @classmethod
    def not_in_future(cls, value: date | None) -> date | None:
        if value and value > date.today():
            raise ValueError("No podés haber aprendido algo en el futuro")
        return value


class EntryCreate(EntryBase):
    pass


class EntryUpdate(EntryBase):
    pass


class EntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    content: str
    code_snippet: str | None
    language: str | None
    difficulty: Difficulty
    reference_url: str | None
    learned_on: date
    created_at: datetime
    updated_at: datetime
    tags: list[str]

    @field_validator("tags", mode="before")
    @classmethod
    def tags_to_names(cls, value):
        return sorted(t if isinstance(t, str) else t.name for t in value)


class EntryPage(BaseModel):
    items: list[EntryRead]
    total: int
    page: int
    size: int
    pages: int


class SortField(str, Enum):
    learned_on = "learned_on"
    created_at = "created_at"
    title = "title"
    id = "id"


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class TagMatch(str, Enum):
    any = "any"
    all = "all"


class StreakRead(BaseModel):
    current_streak: int = Field(description="Días seguidos (terminando hoy o ayer) con al menos una entry")
    longest_streak: int
    total_entries: int
    active_days: int
    last_entry_on: date | None
