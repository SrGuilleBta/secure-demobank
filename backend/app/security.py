import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# Argon2id con los parámetros por defecto de argon2-cffi (perfil recomendado por la RFC 9106).
_hasher = PasswordHasher()

# Hash de una contraseña inventada: se verifica cuando el usuario no existe, para que el login tarde lo mismo
# exista o no la cuenta (amenaza T-17).
DUMMY_HASH = _hasher.hash("contrasena-que-nunca-se-usa")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def new_token() -> str:
    # 256 bits de un generador criptográficamente seguro.
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def tokens_equal(a: str, b: str) -> bool:
    # Comparación en tiempo constante.
    return hmac.compare_digest(a.encode(), b.encode())
