"""Cliente HTTP genérico para a API REST do sistema .NET.

IMPORTANTE: este módulo NÃO define endpoints. Os caminhos reais (consulta, prioridade,
urgência etc.) só podem ser escritos depois que a documentação da API for confirmada
(veja docs/DIAGNOSTICO.md). Aqui há apenas o transporte: autenticação Bearer, HTTPS,
timeout, verificação de TLS e tradução de falhas em ``IntegrationError``.
"""
from __future__ import annotations

from typing import Any

import requests

from config.settings import ApiSettings


class IntegrationError(Exception):
    """Falha de comunicação ou resposta inesperada da API."""


class IntegrationNotConfiguredError(IntegrationError):
    """A API não foi configurada (variáveis de ambiente ausentes)."""


class DotNetApiClient:
    def __init__(
        self,
        base_url: str,
        token: str | None = None,
        timeout: float = 15.0,
        verify_tls: bool = True,
        session: requests.Session | None = None,
    ) -> None:
        base = base_url.strip().rstrip("/")
        local = base.startswith(("http://localhost", "http://127.0.0.1"))
        if not (base.startswith("https://") or local):
            raise IntegrationError("A URL da API deve usar HTTPS.")
        self._base = base
        self._token = token
        self._timeout = timeout
        self._verify = verify_tls
        self._session = session or requests.Session()

    @classmethod
    def from_settings(cls, api: ApiSettings, session: requests.Session | None = None) -> "DotNetApiClient":
        if not api.base_url:
            raise IntegrationNotConfiguredError("API_BASE_URL não configurada.")
        return cls(
            base_url=api.base_url,
            token=api.token.get_secret_value() if api.token else None,
            timeout=api.timeout_seconds,
            verify_tls=api.verify_tls,
            session=session,
        )

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> Any:
        url = f"{self._base}/{path.lstrip('/')}"
        try:
            resposta = self._session.request(
                method,
                url,
                headers=self._headers(),
                params=params,
                json=json,
                timeout=self._timeout,
                verify=self._verify,
            )
        except requests.RequestException as exc:
            raise IntegrationError(
                f"Falha de comunicação com a API ({type(exc).__name__})."
            ) from exc

        if resposta.status_code in (401, 403):
            raise IntegrationError(
                f"A API recusou as credenciais (HTTP {resposta.status_code})."
            )
        if not resposta.ok:
            raise IntegrationError(f"A API retornou HTTP {resposta.status_code}.")
        if resposta.status_code == 204 or not resposta.content:
            return None
        try:
            return resposta.json()
        except ValueError as exc:
            raise IntegrationError("A resposta da API não é um JSON válido.") from exc

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self.request_json("GET", path, params=params)

    def post_json(self, path: str, json: Any = None) -> Any:
        return self.request_json("POST", path, json=json)

    def patch_json(self, path: str, json: Any = None) -> Any:
        return self.request_json("PATCH", path, json=json)
