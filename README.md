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
pip install -r requirements-dev.txt
copy .env.example .env          # opcional

python -m scripts.seed          # opcional: carga 10 entries de ejemplo
fastapi dev app/main.py
```

- Front: http://127.0.0.1:8000
- Docs interactivas de la API: http://127.0.0.1:8000/docs

Tests:

```powershell
pytest                                                              # SQLite en memoria
$env:TEST_DATABASE_URL="postgresql://user@localhost/devlog_test"; pytest   # contra Postgres
```

## Deploy (Render + Neon)

La app se publica en [Render](https://render.com) (plan free) y guarda los datos en Postgres de [Neon](https://neon.tech) (free, no vence). La configuración está en `render.yaml`.

1. **Neon:** crear un proyecto y copiar la *connection string* (`postgresql://...?sslmode=require`).
2. **Render:** *New → Blueprint*, elegir este repo. Pide dos variables:
   - `DATABASE_URL`: la connection string de Neon
   - `ADMIN_KEY`: una clave larga inventada por vos (es la que pide el front para crear/editar/borrar)
3. Cada push a `main` redeploya solo.

Para cargar los datos de ejemplo en Neon (opcional), desde tu máquina:

```powershell
$env:DATABASE_URL="postgresql://...neon..."; python -m scripts.seed
```

> El plan free de Render apaga el servicio después de ~15 min sin visitas; la primera visita después tarda ~1 minuto en despertar. Los datos no se pierden porque están en Neon.

### Clave de admin

Mientras no haya usuarios, la escritura se protege con `ADMIN_KEY`:
- Leer (home, entries, calendario, `GET` de la API) es público.
- `POST`/`PUT`/`DELETE` piden el header `X-Admin-Key`. El front la pide en un diálogo la primera vez y la recuerda en el navegador.
- Si `ADMIN_KEY` está vacía (desarrollo local), la escritura queda abierta.

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

- [ ] Gestión de usuarios + JWT (reemplaza la clave de admin)
- [ ] Migraciones con Alembic, en lugar de `create_all`
- [ ] Markdown completo en el contenido
- [x] PostgreSQL (Neon) + deploy en Render
