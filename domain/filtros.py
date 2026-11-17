"""Filtros de chamados e função pura que os aplica a uma lista em memória."""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from domain.models import SEM_RESPONSAVEL, Chamado, Prioridade, Status


class FiltroChamados(BaseModel):
    data_inicio: date | None = None
    data_fim: date | None = None
    setores: list[str] = Field(default_factory=list)
    responsaveis: list[str] = Field(default_factory=list)
    status: list[Status] = Field(default_factory=list)
    prioridades: list[Prioridade] = Field(default_factory=list)
    apenas_atrasados: bool = False
    busca: str = ""

    @model_validator(mode="after")
    def _periodo_valido(self) -> "FiltroChamados":
        if self.data_inicio and self.data_fim and self.data_inicio > self.data_fim:
            raise ValueError("data_inicio não pode ser posterior a data_fim.")
        return self


def aplicar_filtro(
    chamados: Iterable[Chamado],
    filtro: FiltroChamados | None = None,
    agora: datetime | None = None,
) -> list[Chamado]:
    """Filtra e ordena (mais recentes primeiro). Listas vazias no filtro = sem restrição."""
    agora = agora or datetime.now()
    termo = (filtro.busca if filtro else "").strip().lower()
    resultado: list[Chamado] = []

    for c in chamados:
        if filtro is not None:
            if filtro.data_inicio and c.data_abertura.date() < filtro.data_inicio:
                continue
            if filtro.data_fim and c.data_abertura.date() > filtro.data_fim:
                continue
            if filtro.setores and c.setor not in filtro.setores:
                continue
            if filtro.responsaveis and (c.responsavel or SEM_RESPONSAVEL) not in filtro.responsaveis:
                continue
            if filtro.status and c.status not in filtro.status:
                continue
            if filtro.prioridades and c.prioridade not in filtro.prioridades:
                continue
            if filtro.apenas_atrasados and not c.esta_atrasado(agora):
                continue
            if termo:
                texto = f"{c.numero} {c.titulo} {c.descricao} {c.solicitante}".lower()
                if termo not in texto:
                    continue
        resultado.append(c)

    return sorted(resultado, key=lambda c: c.data_abertura, reverse=True)
