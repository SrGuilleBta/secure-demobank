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

    # Llave para firmar tokens/sesiones (la usa el módulo de autenticación).
    app_secret_key: SecretStr

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
