from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictInt, model_validator


def _normalize_username(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


# Alfabeto cerrado: sin espacios, símbolos ni caracteres de control.
Username = Annotated[str, BeforeValidator(_normalize_username), Field(pattern=r"^[a-z0-9_]{3,32}$")]


class StrictModel(BaseModel):
    # extra="forbid": un campo no declarado (por ejemplo "role" o "balance") se rechaza con 422 (amenaza T-07).
    model_config = ConfigDict(extra="forbid")


class RegisterRequest(StrictModel):
    username: Username
    password: str = Field(min_length=12, max_length=128)

    @model_validator(mode="after")
    def password_differs_from_username(self) -> "RegisterRequest":
        if self.password.lower() == self.username:
            raise ValueError("La contraseña no puede ser igual al usuario")
        return self


class LoginRequest(StrictModel):
    username: Username
    password: str = Field(min_length=1, max_length=128)


class TransferRequest(StrictModel):
    to_username: Username
    # StrictInt: rechaza decimales ("10.5"), textos ("100") y booleanos. El monto va en centavos.
    amount_cents: StrictInt = Field(gt=0, le=1_000_000)
    concept: str = Field(default="", max_length=100)
    idempotency_key: UUID


class UserOut(BaseModel):
    id: UUID
    username: str
    role: str


class LoginOut(BaseModel):
    username: str
    role: str
    csrf_token: str


class AccountOut(BaseModel):
    balance_cents: int


class TransferOut(BaseModel):
    id: UUID
    from_username: str
    to_username: str
    amount_cents: int
    concept: str
    created_at: datetime


class AdminUserOut(BaseModel):
    id: UUID
    username: str
    role: str
    locked: bool
    created_at: datetime


class AuditOut(BaseModel):
    id: int
    created_at: datetime
    user_id: UUID | None
    action: str
    detail: str | None
    ip: str | None
