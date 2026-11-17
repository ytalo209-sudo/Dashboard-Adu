"""Repositório em memória com dados fictícios. Não acessa nenhum banco."""
from __future__ import annotations

import threading
from datetime import datetime

from domain.filtros import FiltroChamados, aplicar_filtro
from domain.models import Chamado, HistoricoEntry
from repositories.base import ChamadoRepository
from repositories.dados_ficticios import RESPONSAVEIS, gerar_chamados


class MockChamadoRepository(ChamadoRepository):
    def __init__(
        self,
        chamados: list[Chamado] | None = None,
        responsaveis: list[str] | None = None,
    ) -> None:
        base = chamados if chamados is not None else gerar_chamados()
        self._chamados: dict[int, Chamado] = {c.numero: c.model_copy(deep=True) for c in base}
        self._historico: list[HistoricoEntry] = []
        self._responsaveis = list(responsaveis if responsaveis is not None else RESPONSAVEIS)
        self._lock = threading.RLock()

    def listar(
        self, filtro: FiltroChamados | None = None, agora: datetime | None = None
    ) -> list[Chamado]:
        with self._lock:
            copias = [c.model_copy(deep=True) for c in self._chamados.values()]
        return aplicar_filtro(copias, filtro, agora)

    def obter(self, numero: int) -> Chamado | None:
        with self._lock:
            chamado = self._chamados.get(numero)
            return chamado.model_copy(deep=True) if chamado else None

    def salvar(self, chamado: Chamado) -> None:
        with self._lock:
            if chamado.numero not in self._chamados:
                raise KeyError(chamado.numero)
            self._chamados[chamado.numero] = chamado.model_copy(deep=True)

    def historico(self, numero: int) -> list[HistoricoEntry]:
        with self._lock:
            entradas = [h for h in self._historico if h.chamado_numero == numero]
        return sorted(entradas, key=lambda h: h.data_hora, reverse=True)

    def adicionar_historico(self, entrada: HistoricoEntry) -> None:
        with self._lock:
            self._historico.append(entrada)

    def listar_setores(self) -> list[str]:
        with self._lock:
            return sorted({c.setor for c in self._chamados.values()})

    def listar_responsaveis(self) -> list[str]:
        return list(self._responsaveis)
