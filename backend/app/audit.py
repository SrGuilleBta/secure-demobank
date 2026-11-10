from uuid import UUID

from fastapi import Request
from sqlalchemy import Connection, text


def client_ip(request: Request) -> str | None:
    # Uvicorn solo confía en X-Forwarded-For si viene del proxy (FORWARDED_ALLOW_IPS), así que no se puede falsificar.
    return request.client.host if request.client else None


def record(conn: Connection, action: str, user_id: UUID | None = None, detail: str | None = None,
           ip: str | None = None) -> None:
    """Agrega un evento a la bitácora dentro de la transacción en curso.

    Nunca recibe contraseñas, tokens ni datos personales completos (amenaza T-24).
    """
    conn.execute(
        text("INSERT INTO audit_log (user_id, action, detail, ip) VALUES (:user_id, :action, :detail, :ip)"),
        {"user_id": user_id, "action": action, "detail": detail, "ip": ip},
    )
