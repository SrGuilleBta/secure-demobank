from functools import lru_cache

from sqlalchemy import Engine, create_engine

from app.config import get_settings


@lru_cache
def get_engine() -> Engine:
    # hide_parameters evita que valores de consultas (p. ej. datos de usuarios) terminen en mensajes de error.
    return create_engine(get_settings().database_url, pool_pre_ping=True, hide_parameters=True)
