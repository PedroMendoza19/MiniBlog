"""Protección provisoria de la escritura con una clave de admin.

Se reemplaza por autenticación con usuarios + JWT en la próxima etapa.
"""

import secrets
from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import settings


def require_admin(x_admin_key: Annotated[str | None, Header()] = None) -> None:
    if settings.admin_key is None:
        return  # sin clave configurada (desarrollo local): escritura abierta
    if not x_admin_key or not secrets.compare_digest(x_admin_key, settings.admin_key):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Necesitás la clave de admin para hacer esto",
        )
