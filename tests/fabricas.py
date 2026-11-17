"""Auxiliares de teste: relógio controlável, usuários e fábrica de chamados."""
from __future__ import annotations

from datetime import datetime, timedelta

from domain.models import Chamado, Perfil, Status, Usuario

AGORA = datetime(2026, 11, 16, 12, 0, 0)

GESTOR = Usuario(login="gestor", nome="Gestor Teste", perfil=Perfil.GESTOR)
ANALISTA = Usuario(login="analista", nome="Analista Teste", perfil=Perfil.ANALISTA)
LEITOR = Usuario(login="leitor", nome="Leitor Teste", perfil=Perfil.LEITOR)


class Relogio:
    """Relógio falso: ``servico = ChamadoService(repo, relogio=Relogio())``."""

    def __init__(self, inicio: datetime = AGORA) -> None:
        self.atual = inicio

    def __call__(self) -> datetime:
        return self.atual

    def avancar(self, **kwargs: float) -> None:
        self.atual += timedelta(**kwargs)


def criar_chamado(numero: int = 1, **campos) -> Chamado:
    base = dict(
        numero=numero,
        titulo="Computador lento",
        descricao="Demora para abrir programas.",
        solicitante="Ana Ribeiro",
        setor="Financeiro",
        categoria="Lentidão no computador",
        responsavel="Carlos Mendes",
        data_abertura=AGORA - timedelta(hours=10),
        prazo=AGORA + timedelta(hours=14),
        status=Status.ABERTO,
    )
    base.update(campos)
    return Chamado(**base)
