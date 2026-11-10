import re
import unicodedata


def slugify(text: str, max_length: int = 80) -> str:
    """'¿Qué es un decorador?' -> 'que-es-un-decorador'"""
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug[:max_length].rstrip("-") or "entry"
