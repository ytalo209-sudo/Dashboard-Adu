from __future__ import annotations

import pytest
from pydantic import ValidationError

from config.settings import Settings


def test_padroes_seguros():
    s = Settings.from_env(environ={})
    assert s.data_source == "simulado"
    assert s.database.dialect == "sqlite"
    assert s.database.read_only is True
    assert s.database.encrypt is True
    assert s.api.base_url is None and s.api.verify_tls is True


def test_le_variaveis_de_ambiente():
    s = Settings.from_env(
        environ={
            "DATA_SOURCE": "SQL",
            "DB_DIALECT": "MSSQL",
            "DB_HOST": "srv-bd",
            "DB_PORT": "1433",
            "DB_NAME": "chamados",
            "DB_USER": "leitor_ro",
            "DB_PASSWORD": "segredo-super",
            "DB_READ_ONLY": "false",
            "API_BASE_URL": "https://api.exemplo.local",
            "API_TOKEN": "tok-123",
            "API_TIMEOUT_SECONDS": "7.5",
        }
    )
    assert s.data_source == "sql"
    assert s.database.dialect == "mssql"
    assert s.database.port == 1433
    assert s.database.read_only is False
    assert s.database.password.get_secret_value() == "segredo-super"
    assert s.api.timeout_seconds == 7.5


def test_segredos_nao_vazam_em_repr():
    s = Settings.from_env(environ={"DB_PASSWORD": "segredo-super", "API_TOKEN": "tok-123"})
    texto = repr(s) + str(s)
    assert "segredo-super" not in texto
    assert "tok-123" not in texto


def test_porta_invalida():
    with pytest.raises(ValueError, match="DB_PORT"):
        Settings.from_env(environ={"DB_PORT": "abc"})


def test_fonte_de_dados_invalida():
    with pytest.raises(ValidationError):
        Settings.from_env(environ={"DATA_SOURCE": "excel"})
