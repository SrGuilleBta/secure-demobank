import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.config import get_settings
from app.routers import accounts, admin, auth, transfers

logger = logging.getLogger("demobank")

settings = get_settings()

# La documentación interactiva solo existe en desarrollo (la usa ZAP para el escaneo de la API).
app = FastAPI(
    title="Secure DemoBank API",
    docs_url="/api/docs" if settings.is_development else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if settings.is_development else None,
)

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(transfers.router)
app.include_router(admin.router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    # El 422 por defecto de FastAPI devuelve el valor recibido ("input"), que podría ser una contraseña.
    # Aquí solo se informa qué campo falló y por qué.
    errors = [{"campo": ".".join(str(p) for p in error["loc"][1:]), "mensaje": error["msg"]}
              for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(Exception)
async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    # El detalle va al log del servidor; el cliente nunca ve trazas, consultas ni rutas internas (T-14).
    logger.error("Error no controlado", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Error interno"})


@app.get("/api/health", include_in_schema=False)
def health() -> JSONResponse:
    try:
        with db.get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # El detalle va al log del servidor; el cliente solo sabe que el servicio no está disponible.
        logger.exception("Health check: la base de datos no responde")
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return JSONResponse(content={"status": "ok"})
