"""Contrato dos repositórios. Serviços dependem desta interface, nunca de uma implementação.

Para integrar com o ambiente real, basta criar outra classe que implemente estes métodos
(SQL somente leitura, API .NET etc.) sem alterar serviços ou interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from domain.filtros import FiltroChamados
from domain.models import Chamado, HistoricoEntry


class ChamadoRepository(ABC):
    @abstractmethod
    def listar(
        self, filtro: FiltroChamados | None = None, agora: datetime | None = None
    ) -> list[Chamado]: ...

    @abstractmethod
    def obter(self, numero: int) -> Chamado | None: ...

    @abstractmethod
    def salvar(self, chamado: Chamado) -> None: ...

    @abstractmethod
    def historico(self, numero: int) -> list[HistoricoEntry]:
        """Entradas do chamado, da mais recente para a mais antiga."""

    @abstractmethod
    def adicionar_historico(self, entrada: HistoricoEntry) -> None: ...

    @abstractmethod
    def listar_setores(self) -> list[str]: ...

    @abstractmethod
    def listar_responsaveis(self) -> list[str]: ...
