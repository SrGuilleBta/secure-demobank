from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import text

from app import audit, db
from app.deps import CurrentUser, get_current_user, require_csrf
from app.schemas import TransferOut, TransferRequest

router = APIRouter(prefix="/api/transfers", tags=["transferencias"])


def _to_out(row) -> TransferOut:
    return TransferOut(id=row.id, from_username=row.from_username, to_username=row.to_username,
                       amount_cents=row.amount_cents, concept=row.concept, created_at=row.created_at)


@router.post("", status_code=201, response_model=TransferOut)
def create_transfer(body: TransferRequest, request: Request, response: Response,
                    user: CurrentUser = Depends(require_csrf)) -> TransferOut:
    with db.get_engine().begin() as conn:
        receiver = conn.execute(
            text("SELECT id FROM users WHERE username = :username"), {"username": body.to_username}
        ).first()
        if receiver is None:
            raise HTTPException(status_code=404, detail="Destinatario no encontrado")
        if receiver.id == user.id:
            raise HTTPException(status_code=422, detail="No puedes transferirte a ti mismo")

        # Se bloquean ambas cuentas en un orden fijo (por ID): evita que dos transferencias simultáneas lean
        # el mismo saldo (doble gasto) y que se bloqueen entre sí (T-08).
        balances = {
            row.user_id: row.balance_cents
            for row in conn.execute(
                text("SELECT user_id, balance_cents FROM accounts WHERE user_id IN (:a, :b) "
                     "ORDER BY user_id FOR UPDATE"),
                {"a": user.id, "b": receiver.id},
            )
        }
        if balances[user.id] < body.amount_cents:
            raise HTTPException(status_code=409, detail="Saldo insuficiente")

        # La llave de idempotencia evita duplicar la transferencia si la petición se reenvía.
        created = conn.execute(
            text("INSERT INTO transfers (from_user_id, to_user_id, amount_cents, concept, idempotency_key) "
                 "VALUES (:from_id, :to_id, :amount, :concept, :key) "
                 "ON CONFLICT (from_user_id, idempotency_key) DO NOTHING RETURNING id"),
            {"from_id": user.id, "to_id": receiver.id, "amount": body.amount_cents,
             "concept": body.concept.strip(), "key": body.idempotency_key},
        ).first()

        if created is None:  # petición repetida: se devuelve la transferencia original sin mover dinero
            transfer_id = conn.execute(
                text("SELECT id FROM transfers WHERE from_user_id = :id AND idempotency_key = :key"),
                {"id": user.id, "key": body.idempotency_key},
            ).scalar_one()
            response.status_code = 200
        else:
            transfer_id = created.id
            conn.execute(
                text("UPDATE accounts SET balance_cents = balance_cents - :amount WHERE user_id = :id"),
                {"amount": body.amount_cents, "id": user.id},
            )
            conn.execute(
                text("UPDATE accounts SET balance_cents = balance_cents + :amount WHERE user_id = :id"),
                {"amount": body.amount_cents, "id": receiver.id},
            )
            audit.record(conn, "transfer", user.id, detail=f"{body.amount_cents} centavos a {body.to_username}",
                         ip=audit.client_ip(request))

        row = conn.execute(
            text("SELECT id, from_username, to_username, amount_cents, concept, created_at "
                 "FROM transfer_details WHERE id = :id"),
            {"id": transfer_id},
        ).one()
    return _to_out(row)


@router.get("", response_model=list[TransferOut])
def list_transfers(page: int = Query(1, ge=1, le=10_000), page_size: int = Query(20, ge=1, le=50),
                   user: CurrentUser = Depends(get_current_user)) -> list[TransferOut]:
    # Tamaño de página con tope (T-19) y solo las transferencias en las que participa el usuario (T-13).
    with db.get_engine().connect() as conn:
        rows = conn.execute(
            text("SELECT id, from_username, to_username, amount_cents, concept, created_at "
                 "FROM transfer_details WHERE from_user_id = :id OR to_user_id = :id "
                 "ORDER BY created_at DESC, id LIMIT :limit OFFSET :offset"),
            {"id": user.id, "limit": page_size, "offset": (page - 1) * page_size},
        ).all()
    return [_to_out(row) for row in rows]


@router.get("/{transfer_id}", response_model=TransferOut)
def get_transfer(transfer_id: UUID, user: CurrentUser = Depends(get_current_user)) -> TransferOut:
    with db.get_engine().connect() as conn:
        row = conn.execute(
            text("SELECT id, from_username, to_username, amount_cents, concept, created_at "
                 "FROM transfer_details WHERE id = :tid AND (from_user_id = :id OR to_user_id = :id)"),
            {"tid": transfer_id, "id": user.id},
        ).first()
    # Si la transferencia existe pero es de otros, también se responde 404: no se confirma que exista (IDOR, T-13).
    if row is None:
        raise HTTPException(status_code=404, detail="No encontrado")
    return _to_out(row)
