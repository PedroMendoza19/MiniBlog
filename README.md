# til/ — Dev Log

Un mini blog de **"Today I Learned"**: notas cortas de cosas que fui aprendiendo programando, con snippet de código, nivel de dificultad, tags y una racha de días seguidos aprendiendo.

API REST con FastAPI + un front server-side simple (Jinja2, sin frameworks de JS), inspirado en la estructura de [cgldev/fastapi-miniblog](https://github.com/cgldev/fastapi-miniblog).

## Stack

- Python 3.10+
- FastAPI · Pydantic v2 · SQLAlchemy 2
- SQLite (desarrollo)
- Jinja2 + CSS propio + highlight.js (front)
- pytest

## Estructura

```
app/
├── main.py                  # app, routers y archivos estáticos
├── core/
│   ├── config.py            # settings desde .env
│   ├── db.py                # engine, sesión, Base
│   └── slug.py              # "¿Qué es X?" -> "que-es-x"
├── models/
│   ├── entry.py             # Entry + tabla intermedia entry_tags
│   └── tag.py
├── api/v1/
│   ├── entries/
│   │   ├── router.py        # endpoints HTTP
│   │   ├── repository.py    # acceso a datos y lógica (búsqueda, racha…)
│   │   └── schemas.py       # validación con Pydantic
│   └── tags/router.py       # /tags y /languages con conteos
└── web/
    ├── router.py            # páginas HTML
    ├── templates/           # Jinja2
    └── static/              # style.css, app.js
scripts/seed.py              # datos de ejemplo
tests/                       # pytest
```

## Cómo correrlo

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # opcional

python -m scripts.seed          # opcional: carga 10 entries de ejemplo
fastapi dev app/main.py
```

- Front: http://127.0.0.1:8000
- Docs interactivas de la API: http://127.0.0.1:8000/docs

Tests:

```powershell
pytest
```

## API

Todas las rutas van bajo `/api/v1`.

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/entries` | Lista paginada con búsqueda, filtros y orden |
| GET | `/entries/random` | Una entry al azar (acepta los mismos filtros) |
| GET | `/entries/streak` | Racha actual, récord, total y días activos |
| GET | `/entries/{slug}` | Una entry |
| POST | `/entries` | Crear (el slug se genera a partir del título) |
| PUT | `/entries/{slug}` | Editar (el slug no cambia, así los links no se rompen) |
| DELETE | `/entries/{slug}` | Borrar |
| GET | `/tags` | Tags en uso con cantidad de entries |
| GET | `/languages` | Lenguajes en uso con cantidad de entries |

Parámetros de `GET /entries`:

- `q`: busca en título y contenido
- `tags`: uno o más (`?tags=python&tags=sql`), con `tag_match=any|all`
- `language`, `difficulty` (`beginner` | `intermediate` | `advanced`)
- `page`, `size` (máximo 50)
- `sort` (`learned_on` | `created_at` | `title` | `id`), `order` (`asc` | `desc`)

Ejemplo de entry:

```json
{
  "title": "El walrus operator existe",
  "content": "Con `:=` podés asignar dentro de una expresión.",
  "code_snippet": "if (n := len(items)) > 10:\n    print(n)",
  "language": "python",
  "difficulty": "beginner",
  "reference_url": "https://peps.python.org/pep-0572/",
  "learned_on": "2026-11-10",
  "tags": ["python", "syntax"]
}
```

## Front

- Home con buscador (atajo `/`), filtros por lenguaje, nivel y tag, y paginación
- Panel con la racha y un heatmap de actividad de las últimas 20 semanas
- Vista de entry con resaltado de sintaxis y botón para copiar el código
- Formulario para crear y editar con tags como chips (`Ctrl+Enter` publica), que muestra los errores de validación de la API en cada campo
- Modo claro y oscuro (sigue al sistema y se puede cambiar a mano)
- Responsive

## Próximos pasos

- [ ] Autenticación JWT: lectura pública, escritura solo con login
- [ ] Migraciones con Alembic, en lugar de `create_all`
- [ ] PostgreSQL + Docker
- [ ] Markdown completo en el contenido
- [ ] Deploy
