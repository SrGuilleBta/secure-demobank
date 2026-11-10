from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app import audit, db
from app.config import get_settings
from app.deps import SESSION_COOKIE, CurrentUser, require_csrf
from app.schemas import LoginOut, LoginRequest, RegisterRequest, UserOut
from app.security import DUMMY_HASH, hash_password, new_token, token_digest, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])

INVALID_CREDENTIALS = "Credenciales inválidas"


@router.post("/register", status_code=201, response_model=UserOut)
def register(body: RegisterRequest, request: Request) -> UserOut:
    settings = get_settings()
    password_hash = hash_password(body.password)
    try:
        with db.get_engine().begin() as conn:
            # El rol NO viene del cliente: toda cuenta nueva es "cliente" (default de la tabla) (amenaza T-07).
            user = conn.execute(
                text("INSERT INTO users (username, password_hash) VALUES (:username, :hash) "
                     "RETURNING id, username, role"),
                {"username": body.username, "hash": password_hash},
            ).one()
            conn.execute(
                text("INSERT INTO accounts (user_id, balance_cents) VALUES (:id, :balance)"),
                {"id": user.id, "balance": settings.initial_balance_cents},
            )
            audit.record(conn, "register", user.id, ip=audit.client_ip(request))
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Usuario no disponible") from None
    return UserOut(id=user.id, username=user.username, role=user.role)


@router.post("/login", response_model=LoginOut)
def login(body: LoginRequest, request: Request, response: Response) -> LoginOut:
    settings = get_settings()
    ip = audit.client_ip(request)
    token = new_token()
    csrf_token = new_token()
    result: LoginOut | None = None

    with db.get_engine().begin() as conn:
        # FOR UPDATE: dos intentos simultáneos contra la misma cuenta no se saltan el contador de fallos.
        user = conn.execute(
            text("SELECT id, username, role, password_hash, failed_attempts, "
                 "(locked_until IS NOT NULL AND locked_until > now()) AS locked "
                 "FROM users WHERE username = :username FOR UPDATE"),
            {"username": body.username},
        ).first()

        # Se verifica siempre un hash, exista o no el usuario, para no revelar cuentas por el tiempo de respuesta.
        valid = verify_password(user.password_hash if user else DUMMY_HASH, body.password)

        if user is not None and valid and not user.locked:
            conn.execute(
                text("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = :id"), {"id": user.id}
            )
            conn.execute(text("DELETE FROM sessions WHERE expires_at < now()"))
            conn.execute(
                text("INSERT INTO sessions (token_hash, user_id, csrf_token, expires_at) "
                     "VALUES (:hash, :user_id, :csrf, now() + make_interval(mins => :ttl))"),
                {"hash": token_digest(token), "user_id": user.id, "csrf": csrf_token,
                 "ttl": settings.session_ttl_minutes},
            )
            audit.record(conn, "login_ok", user.id, ip=ip)
            result = LoginOut(username=user.username, role=user.role, csrf_token=csrf_token)
        elif user is None:
            audit.record(conn, "login_failed", detail="usuario desconocido", ip=ip)
        elif not user.locked:
            failed = user.failed_attempts + 1
            if failed >= settings.max_failed_attempts:
                conn.execute(
                    text("UPDATE users SET failed_attempts = 0, "
                         "locked_until = now() + make_interval(mins => :minutes) WHERE id = :id"),
                    {"minutes": settings.lockout_minutes, "id": user.id},
                )
                audit.record(conn, "account_locked", user.id, ip=ip)
            else:
                conn.execute(
                    text("UPDATE users SET failed_attempts = :failed WHERE id = :id"),
                    {"failed": failed, "id": user.id},
                )
            audit.record(conn, "login_failed", user.id, ip=ip)
        else:
            audit.record(conn, "login_blocked", user.id, ip=ip)

    # La respuesta es idéntica en todos los fallos (usuario inexistente, clave mala o cuenta bloqueada).
    # Se lanza fuera de la transacción para que el contador de fallos y la bitácora sí se guarden.
    if result is None:
        raise HTTPException(status_code=401, detail=INVALID_CREDENTIALS)

    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_minutes * 60,
        httponly=True,  # JavaScript no puede leerla (mitiga el robo por XSS, T-02)
        samesite="strict",  # el navegador no la envía desde otros sitios (mitiga CSRF, T-09)
        secure=settings.cookie_secure,
        path="/",
    )
    return result


@router.post("/logout", status_code=204)
def logout(request: Request, user: CurrentUser = Depends(require_csrf)) -> Response:
    token = request.cookies.get(SESSION_COOKIE, "")
    with db.get_engine().begin() as conn:
        # Se borra en el servidor: el token deja de servir aunque alguien lo haya copiado.
        conn.execute(text("DELETE FROM sessions WHERE token_hash = :hash"), {"hash": token_digest(token)})
        audit.record(conn, "logout", user.id, ip=audit.client_ip(request))
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response
