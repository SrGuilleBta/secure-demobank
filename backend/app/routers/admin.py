from fastapi import APIRouter, Depends, Query
from sqlalchemy import text

from app import db
from app.deps import require_admin
from app.schemas import AdminUserOut, AuditOut

# Todo el router exige rol administrador; un cliente recibe 403 en cualquier ruta de aquí (amenaza T-20).
router = APIRouter(prefix="/api/admin", tags=["administración"], dependencies=[Depends(require_admin)])


@router.get("/users", response_model=list[AdminUserOut])
def list_users(page: int = Query(1, ge=1, le=10_000), page_size: int = Query(20, ge=1, le=50)) -> list[AdminUserOut]:
    with db.get_engine().connect() as conn:
        rows = conn.execute(
            text("SELECT id, username, role, (locked_until IS NOT NULL AND locked_until > now()) AS locked, "
                 "created_at FROM users ORDER BY created_at, id LIMIT :limit OFFSET :offset"),
            {"limit": page_size, "offset": (page - 1) * page_size},
        ).all()
    return [AdminUserOut(id=r.id, username=r.username, role=r.role, locked=r.locked, created_at=r.created_at)
            for r in rows]


@router.get("/audit", response_model=list[AuditOut])
def list_audit(page: int = Query(1, ge=1, le=10_000), page_size: int = Query(20, ge=1, le=50)) -> list[AuditOut]:
    with db.get_engine().connect() as conn:
        rows = conn.execute(
            text("SELECT id, created_at, user_id, action, detail, ip FROM audit_log "
                 "ORDER BY id DESC LIMIT :limit OFFSET :offset"),
            {"limit": page_size, "offset": (page - 1) * page_size},
        ).all()
    return [AuditOut(id=r.id, created_at=r.created_at, user_id=r.user_id, action=r.action, detail=r.detail,
                     ip=r.ip) for r in rows]
