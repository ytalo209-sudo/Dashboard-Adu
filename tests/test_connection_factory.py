from __future__ import annotations

import sys

import pytest

from config.settings import DatabaseSettings
from database.connection_factory import ConnectionFactory
from database.exceptions import DatabaseConfigError, DependencyMissingError


def _mssql(**extra) -> DatabaseSettings:
    base = dict(dialect="mssql", host="srv", port=1433, name="chamados", user="ro", password="senha-secreta")
    base.update(extra)
    return DatabaseSettings(**base)


def test_sqlite_padrao_em_memoria():
    partes = ConnectionFactory(DatabaseSettings()).url_parts()
    assert partes.drivername == "sqlite"
    assert partes.database == ":memory:"


def test_mssql_usa_odbc_e_criptografia():
    partes = ConnectionFactory(_mssql()).url_parts()
    assert partes.drivername == "mssql+pyodbc"
    assert partes.query["driver"] == "ODBC Driver 18 for SQL Server"
    assert partes.query["Encrypt"] == "yes"
    assert partes.query["TrustServerCertificate"] == "no"
    assert partes.host == "srv" and partes.port == 1433


def test_trocar_de_banco_so_muda_a_configuracao():
    pg = ConnectionFactory(_mssql(dialect="postgresql")).url_parts()
    assert pg.drivername == "postgresql+psycopg2"
    assert pg.query == {"sslmode": "require"}


def test_variaveis_ausentes_sao_listadas_sem_vazar_segredos():
    fabrica = ConnectionFactory(DatabaseSettings(dialect="mssql", host="srv", password="senha-secreta"))
    with pytest.raises(DatabaseConfigError) as erro:
        fabrica.url_parts()
    mensagem = str(erro.value)
    assert "DB_NAME" in mensagem and "DB_USER" in mensagem
    assert "senha-secreta" not in mensagem


def test_dialeto_nao_suportado():
    with pytest.raises(DatabaseConfigError, match="não suportado"):
        ConnectionFactory(DatabaseSettings(dialect="oracle")).url_parts()


def test_senha_nao_aparece_no_repr_das_partes():
    assert "senha-secreta" not in repr(ConnectionFactory(_mssql()).url_parts())


def test_sem_sqlalchemy_o_erro_e_claro(monkeypatch):
    monkeypatch.setitem(sys.modules, "sqlalchemy", None)  # simula pacote ausente
    with pytest.raises(DependencyMissingError, match="pip install sqlalchemy"):
        ConnectionFactory(DatabaseSettings()).engine()


# ---- Os testes abaixo exigem SQLAlchemy instalado; sem ele, são pulados ----
def test_sqlite_em_memoria_conecta_e_executa():
    sa = pytest.importorskip("sqlalchemy")
    fabrica = ConnectionFactory(DatabaseSettings(dialect="sqlite", name=":memory:"))
    assert fabrica.test_connection() is True
    with fabrica.session_scope() as sessao:
        assert sessao.execute(sa.text("SELECT 41 + 1")).scalar() == 42
    assert fabrica.engine() is fabrica.engine()  # engine reutilizado
    fabrica.dispose()


def test_sessao_somente_leitura_nao_persiste(tmp_path):
    sa = pytest.importorskip("sqlalchemy")
    arquivo = tmp_path / "teste.db"
    fabrica = ConnectionFactory(DatabaseSettings(dialect="sqlite", name=str(arquivo)))
    with fabrica.session_scope(read_only=False) as sessao:
        sessao.execute(sa.text("CREATE TABLE t (x INTEGER)"))
    with fabrica.session_scope(read_only=True) as sessao:
        sessao.execute(sa.text("INSERT INTO t VALUES (1)"))
    with fabrica.session_scope(read_only=True) as sessao:
        assert sessao.execute(sa.text("SELECT COUNT(*) FROM t")).scalar() == 0
    fabrica.dispose()
