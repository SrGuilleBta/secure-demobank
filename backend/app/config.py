from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    """Configuración leída de variables de entorno y de Docker secrets (/run/secrets/<campo>).

    Los secretos son SecretStr: no aparecen en repr(), logs ni trazas de error.
    """

    model_config = SettingsConfigDict(secrets_dir="/run/secrets")

    # Seguro por defecto: si nadie dice lo contrario, se comporta como producción (sin /api/docs).
    app_env: Literal["development", "production"] = "production"

    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "demobank"
    db_user: str = "demobank_app"
    db_app_password: SecretStr

    # Reservada para firmar datos de la aplicación. Las sesiones no la usan: son tokens aleatorios guardados
    # (solo su hash) en la tabla sessions.
    app_secret_key: SecretStr

    # Reglas de autenticación.
    session_ttl_minutes: int = 30  # expira por inactividad; cada petición autenticada la renueva
    max_failed_attempts: int = 5  # intentos fallidos antes de bloquear la cuenta
    lockout_minutes: int = 15
    cookie_secure: bool = False  # True cuando el sitio se sirva por HTTPS

    # Saldo con el que nace cada cuenta (dinero ficticio de la demo), en centavos.
    initial_balance_cents: int = 100_000

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def database_url(self) -> URL:
        return URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_app_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
