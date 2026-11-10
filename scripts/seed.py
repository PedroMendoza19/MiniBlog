"""Carga entries de ejemplo para ver el front con contenido.

Uso:  python -m scripts.seed          (agrega solo si la base está vacía)
      python -m scripts.seed --reset  (borra todo y vuelve a cargar)
"""

import sys
from datetime import date, timedelta

from sqlalchemy import func, select

from app import models  # noqa: F401
from app.api.v1.entries.repository import create_entry
from app.api.v1.entries.schemas import EntryCreate
from app.core.db import Base, SessionLocal, engine
from app.models import Entry

today = date.today()

SAMPLES = [
    dict(
        days_ago=0,
        title="El walrus operator ahorra una línea (y una llamada)",
        content="Con `:=` podés asignar dentro de una expresión. Sirve mucho en `while` y comprensiones, "
        "cuando necesitás el valor para la condición **y** para usarlo después.\n\n"
        "Ojo: no abusar. Si la línea se vuelve difícil de leer, mejor dos líneas.",
        code_snippet='while (chunk := f.read(8192)):\n    process(chunk)\n\nif (n := len(items)) > 10:\n    print(f"Demasiados items: {n}")',
        language="python",
        difficulty="beginner",
        reference_url="https://peps.python.org/pep-0572/",
        tags=["python", "syntax"],
    ),
    dict(
        days_ago=1,
        title="CTEs recursivas para recorrer árboles en SQL",
        content="Con `WITH RECURSIVE` se puede recorrer una tabla con `parent_id` sin hacer N queries. "
        "La primera parte es el caso base y la segunda se une con el resultado anterior.",
        code_snippet="WITH RECURSIVE tree AS (\n  SELECT id, name, parent_id, 0 AS depth\n  FROM categories WHERE parent_id IS NULL\n  UNION ALL\n  SELECT c.id, c.name, c.parent_id, t.depth + 1\n  FROM categories c JOIN tree t ON c.parent_id = t.id\n)\nSELECT * FROM tree ORDER BY depth;",
        language="sql",
        difficulty="advanced",
        tags=["sql", "postgres"],
    ),
    dict(
        days_ago=2,
        title="git commit --fixup + rebase --autosquash",
        content="Para corregir un commit viejo sin perder la cabeza: `git commit --fixup <sha>` y después "
        "`git rebase -i --autosquash <base>`. El fixup se ordena solo al lado del commit original.",
        code_snippet="git commit --fixup a1b2c3d\ngit rebase -i --autosquash main",
        language="bash",
        difficulty="intermediate",
        tags=["git"],
    ),
    dict(
        days_ago=3,
        title="Depends() en FastAPI también sirve para agrupar query params",
        content="Si varios endpoints comparten filtros, se puede hacer una clase y usarla con `Depends()`. "
        "FastAPI lee el `__init__` y arma los query params solo. Menos código repetido.",
        code_snippet="class Filters:\n    def __init__(self, q: str | None = None, tag: str | None = None):\n        self.q, self.tag = q, tag\n\n@app.get(\"/items\")\ndef items(f: Annotated[Filters, Depends()]):\n    ...",
        language="python",
        difficulty="intermediate",
        reference_url="https://fastapi.tiangolo.com/tutorial/dependencies/classes-as-dependencies/",
        tags=["python", "fastapi"],
    ),
    dict(
        days_ago=5,
        title="Multi-stage builds para imágenes Docker livianas",
        content="Compilás en una etapa con todas las herramientas y copiás solo el resultado a una imagen mínima. "
        "Pasé de 900 MB a 120 MB.",
        code_snippet="FROM python:3.12 AS build\nRUN pip wheel -r requirements.txt -w /wheels\n\nFROM python:3.12-slim\nCOPY --from=build /wheels /wheels\nRUN pip install /wheels/*",
        language="dockerfile",
        difficulty="intermediate",
        tags=["docker", "devops"],
    ),
    dict(
        days_ago=6,
        title="structuredClone() existe y copia en profundidad",
        content="Ya no hace falta `JSON.parse(JSON.stringify(obj))`. `structuredClone` copia en profundidad "
        "y además soporta `Date`, `Map`, `Set` y referencias circulares.",
        code_snippet="const copy = structuredClone(original);\ncopy.nested.value = 42; // original intacto",
        language="javascript",
        difficulty="beginner",
        reference_url="https://developer.mozilla.org/en-US/docs/Web/API/structuredClone",
        tags=["javascript", "web"],
    ),
    dict(
        days_ago=9,
        title="El orden de los índices compuestos importa",
        content="Un índice en `(user_id, created_at)` sirve para filtrar por `user_id` o por los dos, "
        "pero **no** para filtrar solo por `created_at`. Regla: la columna más filtrada primero.",
        language="sql",
        difficulty="intermediate",
        tags=["sql", "performance"],
    ),
    dict(
        days_ago=12,
        title="Los defaults mutables en Python son una trampa",
        content="`def f(x=[])` crea la lista **una sola vez**, cuando se define la función. "
        "Se comparte entre llamadas. Usar `None` y crearla adentro.",
        code_snippet="def add(item, items=None):\n    items = [] if items is None else items\n    items.append(item)\n    return items",
        language="python",
        difficulty="beginner",
        tags=["python", "gotchas"],
    ),
    dict(
        days_ago=13,
        title="CSS: color-mix() para variantes de un color",
        content="`color-mix(in srgb, var(--accent) 20%, transparent)` genera un tono suave sin tener que "
        "definir otra variable. Ideal para hovers y fondos.",
        code_snippet=".chip:hover {\n  background: color-mix(in srgb, var(--accent) 15%, transparent);\n}",
        language="css",
        difficulty="beginner",
        tags=["css", "web"],
    ),
    dict(
        days_ago=20,
        title="pytest: fixtures con yield para setup y teardown",
        content="Todo lo que va antes del `yield` es el setup, y lo que va después es la limpieza. "
        "Se ejecuta aunque el test falle.",
        code_snippet="@pytest.fixture\ndef db():\n    conn = connect()\n    yield conn\n    conn.close()",
        language="python",
        difficulty="beginner",
        tags=["python", "testing"],
    ),
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if "--reset" in sys.argv:
            for entry in db.scalars(select(Entry)):
                db.delete(entry)
            db.commit()
        elif db.scalar(select(func.count(Entry.id))):
            print("La base ya tiene entries; usá --reset para recargar.")
            return
        for sample in SAMPLES:
            data = dict(sample)
            data["learned_on"] = today - timedelta(days=data.pop("days_ago"))
            create_entry(db, EntryCreate(**data))
        print(f"Listo: {len(SAMPLES)} entries cargadas.")


if __name__ == "__main__":
    main()
