from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from app import models  # noqa: F401  (registra los modelos en Base.metadata)
from app.api.v1.entries.router import router as entries_router
from app.api.v1.tags.router import router as tags_router
from app.core.config import settings
from app.core.db import Base, engine
from app.core.security import require_admin
from app.web.router import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Atajo de desarrollo: se reemplaza por migraciones con Alembic más adelante.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    description="API de un Dev Log / TIL: notas cortas de cosas que aprendiste programando.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(entries_router, prefix="/api/v1")
app.include_router(tags_router, prefix="/api/v1")
app.include_router(web_router)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "web" / "static"), name="static")


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


@app.get("/api/v1/admin/check", tags=["meta"], dependencies=[Depends(require_admin)])
def admin_check():
    """Devuelve 200 si la clave del header X-Admin-Key es válida (o si no hay clave configurada)."""
    return {"ok": True, "protected": settings.admin_key is not None}
