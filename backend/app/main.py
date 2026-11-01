import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import get_engine

logger = logging.getLogger("demobank")

settings = get_settings()

# La documentación interactiva solo existe en desarrollo (la usa ZAP para el escaneo de la API).
app = FastAPI(
    title="Secure DemoBank API",
    docs_url="/api/docs" if settings.is_development else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if settings.is_development else None,
)


@app.get("/api/health", include_in_schema=False)
def health() -> JSONResponse:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # El detalle va al log del servidor; el cliente solo sabe que el servicio no está disponible.
        logger.exception("Health check: la base de datos no responde")
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return JSONResponse(content={"status": "ok"})
