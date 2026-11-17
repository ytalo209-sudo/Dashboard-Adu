"""Configurações lidas de variáveis de ambiente (``.env`` em desenvolvimento).

Nenhuma credencial fica no código. Segredos usam ``SecretStr`` para não aparecerem
em ``repr()``, logs ou tracebacks.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr

FonteDeDados = Literal["simulado", "sql", "api"]
_VERDADEIROS = {"1", "true", "yes", "sim", "on"}


def _texto(env: Mapping[str, str], chave: str) -> str | None:
    valor = env.get(chave)
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None


def _bool(env: Mapping[str, str], chave: str, padrao: bool) -> bool:
    valor = _texto(env, chave)
    return padrao if valor is None else valor.lower() in _VERDADEIROS


def _numero(env: Mapping[str, str], chave: str, tipo: type, padrao):
    valor = _texto(env, chave)
    if valor is None:
        return padrao
    try:
        return tipo(valor)
    except ValueError:
        raise ValueError(f"Variável {chave} inválida: esperado {tipo.__name__}.") from None


class DatabaseSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    dialect: str = "sqlite"
    host: str | None = None
    port: int | None = None
    name: str | None = None
    user: str | None = None
    password: SecretStr | None = None
    odbc_driver: str = "ODBC Driver 18 for SQL Server"
    encrypt: bool = True
    trust_server_certificate: bool = False
    read_only: bool = True
    pool_size: int = 5


class ApiSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_url: str | None = None
    token: SecretStr | None = None
    timeout_seconds: float = 15.0
    verify_tls: bool = True


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_env: str = "dev"
    data_source: FonteDeDados = "simulado"
    log_level: str = "INFO"
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    api: ApiSettings = Field(default_factory=ApiSettings)

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
        env_file: str | Path | None = None,
    ) -> "Settings":
        """Monta as configurações.

        Sem ``environ``, carrega o ``.env`` (se existir) e usa ``os.environ``.
        Passar ``environ`` explicitamente é útil em testes.
        """
        if environ is None:
            load_dotenv(env_file, override=False)
            environ = os.environ

        senha = environ.get("DB_PASSWORD") or None
        token = environ.get("API_TOKEN") or None

        return cls(
            app_env=_texto(environ, "APP_ENV") or "dev",
            data_source=(_texto(environ, "DATA_SOURCE") or "simulado").lower(),
            log_level=(_texto(environ, "LOG_LEVEL") or "INFO").upper(),
            database=DatabaseSettings(
                dialect=(_texto(environ, "DB_DIALECT") or "sqlite").lower(),
                host=_texto(environ, "DB_HOST"),
                port=_numero(environ, "DB_PORT", int, None),
                name=_texto(environ, "DB_NAME"),
                user=_texto(environ, "DB_USER"),
                password=SecretStr(senha) if senha else None,
                odbc_driver=_texto(environ, "DB_ODBC_DRIVER") or "ODBC Driver 18 for SQL Server",
                encrypt=_bool(environ, "DB_ENCRYPT", True),
                trust_server_certificate=_bool(environ, "DB_TRUST_SERVER_CERTIFICATE", False),
                read_only=_bool(environ, "DB_READ_ONLY", True),
                pool_size=_numero(environ, "DB_POOL_SIZE", int, 5),
            ),
            api=ApiSettings(
                base_url=_texto(environ, "API_BASE_URL"),
                token=SecretStr(token) if token else None,
                timeout_seconds=_numero(environ, "API_TIMEOUT_SECONDS", float, 15.0),
                verify_tls=_bool(environ, "API_VERIFY_TLS", True),
            ),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Configurações únicas da aplicação (lidas uma vez por processo)."""
    return Settings.from_env()
