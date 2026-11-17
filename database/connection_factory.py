"""Connection Factory: único ponto de criação de engines e sessões SQLAlchemy.

Princípios:
- credenciais vêm de ``DatabaseSettings`` (variáveis de ambiente), nunca do código;
- trocar de banco = trocar ``DB_DIALECT`` (+ driver), sem mexer em serviços ou interface;
- o engine é criado sob demanda e reutilizado (pool), evitando conexões desnecessárias;
- por padrão a sessão é somente leitura: nunca faz commit (sempre rollback ao final);
- mensagens de erro não vazam host, usuário ou senha.
"""
from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from config.settings import DatabaseSettings
from database.exceptions import (
    DatabaseConfigError,
    DatabaseConnectionError,
    DependencyMissingError,
)

logger = logging.getLogger(__name__)

# dialeto (variável DB_DIALECT) -> "drivername" do SQLAlchemy
DIALETOS_SUPORTADOS: dict[str, str] = {
    "sqlite": "sqlite",
    "mssql": "mssql+pyodbc",
    "postgresql": "postgresql+psycopg2",
    "mysql": "mysql+pymysql",
}


@dataclass(frozen=True)
class UrlParts:
    """Partes da URL de conexão. Puro Python, por isso testável sem SQLAlchemy."""

    drivername: str
    username: str | None = None
    password: str | None = field(default=None, repr=False)
    host: str | None = None
    port: int | None = None
    database: str | None = None
    query: dict[str, str] = field(default_factory=dict)


def _exigir_sqlalchemy() -> None:
    try:
        import sqlalchemy  # noqa: F401
    except ImportError as exc:
        raise DependencyMissingError(
            "SQLAlchemy não está instalado. Instale com: pip install sqlalchemy"
        ) from exc


class ConnectionFactory:
    def __init__(self, settings: DatabaseSettings) -> None:
        self._settings = settings
        self._engine: Any = None
        self._session_factory: Any = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ URL
    def url_parts(self) -> UrlParts:
        s = self._settings
        dialeto = s.dialect.lower()
        if dialeto not in DIALETOS_SUPORTADOS:
            suportados = ", ".join(sorted(DIALETOS_SUPORTADOS))
            raise DatabaseConfigError(
                f"Dialeto '{s.dialect}' não suportado. Suportados: {suportados}."
            )

        drivername = DIALETOS_SUPORTADOS[dialeto]
        if dialeto == "sqlite":
            return UrlParts(drivername=drivername, database=s.name or ":memory:")

        senha = s.password.get_secret_value() if s.password else ""
        faltando = [
            nome
            for nome, valor in (
                ("DB_HOST", s.host),
                ("DB_NAME", s.name),
                ("DB_USER", s.user),
                ("DB_PASSWORD", senha),
            )
            if not valor
        ]
        if faltando:
            raise DatabaseConfigError(
                "Variáveis de ambiente ausentes: " + ", ".join(faltando) + "."
            )

        query: dict[str, str] = {}
        if dialeto == "mssql":
            query = {
                "driver": s.odbc_driver,
                "Encrypt": "yes" if s.encrypt else "no",
                "TrustServerCertificate": "yes" if s.trust_server_certificate else "no",
            }
        elif dialeto == "postgresql" and s.encrypt:
            query = {"sslmode": "require"}

        return UrlParts(
            drivername=drivername,
            username=s.user,
            password=senha,
            host=s.host,
            port=s.port,
            database=s.name,
            query=query,
        )

    # --------------------------------------------------------------- engine
    def engine(self) -> Any:
        """Engine único (e seu pool de conexões), criado na primeira chamada."""
        if self._engine is None:
            with self._lock:
                if self._engine is None:
                    self._engine = self._criar_engine()
        return self._engine

    def _criar_engine(self) -> Any:
        _exigir_sqlalchemy()
        import sqlalchemy as sa
        from sqlalchemy.engine import URL

        partes = self.url_parts()
        url = URL.create(
            drivername=partes.drivername,
            username=partes.username,
            password=partes.password,  # URL.create escapa caracteres especiais
            host=partes.host,
            port=partes.port,
            database=partes.database,
            query=partes.query,
        )
        opcoes: dict[str, Any] = {"pool_pre_ping": True}
        if partes.drivername != "sqlite":
            opcoes.update(pool_size=self._settings.pool_size, max_overflow=2, pool_recycle=1800)

        try:
            return sa.create_engine(url, **opcoes)
        except Exception as exc:
            logger.error("Falha ao criar engine (%s).", type(exc).__name__)
            raise DatabaseConnectionError(
                "Não foi possível configurar a conexão com o banco de dados."
            ) from exc

    # --------------------------------------------------------------- sessão
    @contextmanager
    def session_scope(self, read_only: bool | None = None) -> Iterator[Any]:
        """Sessão transacional.

        ``read_only=True`` (padrão vem de ``DB_READ_ONLY``): nunca faz commit.
        Mesmo assim, o ideal é o usuário do banco ter apenas permissão de SELECT.
        """
        from sqlalchemy.exc import SQLAlchemyError
        from sqlalchemy.orm import sessionmaker

        somente_leitura = self._settings.read_only if read_only is None else read_only
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine(), expire_on_commit=False)

        sessao = self._session_factory()
        try:
            yield sessao
            if somente_leitura:
                sessao.rollback()
            else:
                sessao.commit()
        except SQLAlchemyError as exc:
            sessao.rollback()
            logger.error("Erro de banco (%s).", type(exc).__name__)
            raise DatabaseConnectionError(
                "Erro ao executar a operação no banco de dados."
            ) from exc
        except Exception:
            sessao.rollback()
            raise
        finally:
            sessao.close()

    def test_connection(self) -> bool:
        """Executa ``SELECT 1``. Retorna True ou levanta DatabaseConnectionError."""
        from sqlalchemy import text

        with self.session_scope(read_only=True) as sessao:
            sessao.execute(text("SELECT 1"))
        return True

    def dispose(self) -> None:
        """Fecha o pool de conexões."""
        with self._lock:
            if self._engine is not None:
                self._engine.dispose()
            self._engine = None
            self._session_factory = None
