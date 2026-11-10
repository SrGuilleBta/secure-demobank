from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import text

from app import db
from app.config import get_settings
from app.security import token_digest, tokens_equal

SESSION_COOKIE = "session"
CSRF_HEADER = "X-CSRF-Token"


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    username: str
    role: str
    csrf_token: str


def get_current_user(request: Request) -> CurrentUser:
    """Usuario de la sesión de la cookie, o 401. Renueva la expiración por inactividad."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="No autenticado")
    with db.get_engine().begin() as conn:
        row = conn.execute(
            text(
                "UPDATE sessions s SET expires_at = now() + make_interval(mins => :ttl) "
                "FROM users u "
                "WHERE s.token_hash = :hash AND s.expires_at > now() AND u.id = s.user_id "
                "RETURNING u.id, u.username, u.role, s.csrf_token"
            ),
            {"ttl": get_settings().session_ttl_minutes, "hash": token_digest(token)},
        ).first()
    if row is None:
        raise HTTPException(status_code=401, detail="No autenticado")
    return CurrentUser(id=row.id, username=row.username, role=row.role, csrf_token=row.csrf_token)


def require_csrf(
    x_csrf_token: str = Header(default="", alias=CSRF_HEADER, description="csrf_token que devolvió el login"),
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Para peticiones que cambian datos: exige el token CSRF que se entregó al iniciar sesión (amenaza T-09).

    Se declara como Header para que aparezca en la documentación (/api/docs) y se pueda probar desde ahí.
    """
    if not tokens_equal(x_csrf_token, user.csrf_token):
        raise HTTPException(status_code=403, detail="Token CSRF inválido")
    return user


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    # El rol sale de la base de datos, nunca de lo que envíe el cliente (amenaza T-20).
    if user.role != "administrador":
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return user
