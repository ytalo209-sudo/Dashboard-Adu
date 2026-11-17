from __future__ import annotations

import pytest
import requests

from config.settings import ApiSettings
from integrations.dotnet_api_client import (
    DotNetApiClient,
    IntegrationError,
    IntegrationNotConfiguredError,
)


class RespostaFalsa:
    def __init__(self, status=200, corpo=None, conteudo=b"{}"):
        self.status_code = status
        self.ok = status < 400
        self._corpo = {} if corpo is None else corpo
        self.content = conteudo

    def json(self):
        if isinstance(self._corpo, Exception):
            raise self._corpo
        return self._corpo


class SessaoFalsa:
    def __init__(self, resposta=None, erro=None):
        self.resposta = resposta or RespostaFalsa()
        self.erro = erro
        self.chamadas = []

    def request(self, metodo, url, **kwargs):
        self.chamadas.append((metodo, url, kwargs))
        if self.erro:
            raise self.erro
        return self.resposta


def _cliente(sessao, **kw):
    return DotNetApiClient("https://api.exemplo.local/", token="tok-123", session=sessao, **kw)


def test_envia_token_bearer_url_e_parametros():
    sessao = SessaoFalsa(RespostaFalsa(corpo={"ok": True}))
    resultado = _cliente(sessao, timeout=5, verify_tls=True).get_json("/algum/caminho", params={"a": 1})
    metodo, url, kwargs = sessao.chamadas[0]
    assert resultado == {"ok": True}
    assert (metodo, url) == ("GET", "https://api.exemplo.local/algum/caminho")
    assert kwargs["headers"]["Authorization"] == "Bearer tok-123"
    assert kwargs["timeout"] == 5 and kwargs["verify"] is True
    assert kwargs["params"] == {"a": 1}


def test_exige_https_exceto_localhost():
    with pytest.raises(IntegrationError, match="HTTPS"):
        DotNetApiClient("http://servidor-interno/api")
    DotNetApiClient("http://localhost:5000/api")  # permitido para desenvolvimento


def test_credenciais_recusadas():
    with pytest.raises(IntegrationError, match="401"):
        _cliente(SessaoFalsa(RespostaFalsa(status=401))).get_json("x")


def test_erro_http_generico_nao_vaza_corpo():
    with pytest.raises(IntegrationError, match="HTTP 500"):
        _cliente(SessaoFalsa(RespostaFalsa(status=500))).get_json("x")


def test_falha_de_rede_vira_integration_error():
    sessao = SessaoFalsa(erro=requests.ConnectionError("detalhe interno com host"))
    with pytest.raises(IntegrationError) as erro:
        _cliente(sessao).get_json("x")
    assert "detalhe interno" not in str(erro.value)


def test_204_retorna_none_e_json_invalido_falha():
    assert _cliente(SessaoFalsa(RespostaFalsa(status=204, conteudo=b""))).patch_json("x", json={}) is None
    with pytest.raises(IntegrationError, match="JSON"):
        _cliente(SessaoFalsa(RespostaFalsa(corpo=ValueError("x"), conteudo=b"<html>"))).get_json("x")


def test_from_settings_sem_url_configurada():
    with pytest.raises(IntegrationNotConfiguredError):
        DotNetApiClient.from_settings(ApiSettings())
