from fastapi import APIRouter, Depends
from sqlalchemy import text

from app import db
from app.deps import CurrentUser, get_current_user
from app.schemas import AccountOut, UserOut

router = APIRouter(prefix="/api", tags=["cuenta"])


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, username=user.username, role=user.role)


@router.get("/account", response_model=AccountOut)
def account(user: CurrentUser = Depends(get_current_user)) -> AccountOut:
    # La cuenta sale de la sesión, nunca de un ID enviado por el cliente (amenaza T-13).
    with db.get_engine().connect() as conn:
        balance = conn.execute(
            text("SELECT balance_cents FROM accounts WHERE user_id = :id"), {"id": user.id}
        ).scalar_one()
    return AccountOut(balance_cents=balance)
