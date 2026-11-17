from __future__ import annotations

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from domain.filtros import FiltroChamados, aplicar_filtro
from domain.models import SEM_RESPONSAVEL, Prioridade, Status
from tests.fabricas import AGORA, criar_chamado


def test_chamado_concluido_exige_data_de_conclusao():
    with pytest.raises(ValidationError):
        criar_chamado(status=Status.CONCLUIDO)


def test_data_de_conclusao_so_para_concluido():
    with pytest.raises(ValidationError):
        criar_chamado(data_conclusao=AGORA)


def test_conclusao_nao_pode_ser_anterior_a_abertura():
    with pytest.raises(ValidationError):
        criar_chamado(status=Status.CONCLUIDO, data_conclusao=AGORA - timedelta(days=5))


def test_esta_atrasado():
    vencido = criar_chamado(1, prazo=AGORA - timedelta(hours=1))
    no_prazo = criar_chamado(2, prazo=AGORA + timedelta(hours=1))
    concluido_vencido = criar_chamado(
        3, prazo=AGORA - timedelta(hours=1), status=Status.CONCLUIDO, data_conclusao=AGORA - timedelta(hours=2)
    )
    assert vencido.esta_atrasado(AGORA)
    assert not no_prazo.esta_atrasado(AGORA)
    assert not concluido_vencido.esta_atrasado(AGORA)


def test_filtro_rejeita_periodo_invertido():
    with pytest.raises(ValidationError):
        FiltroChamados(data_inicio=date(2026, 11, 10), data_fim=date(2026, 11, 1))


def _base():
    return [
        criar_chamado(1, setor="Financeiro", prioridade=Prioridade.CRITICA, titulo="Impressora parada"),
        criar_chamado(2, setor="RH", responsavel=None, prazo=AGORA - timedelta(hours=3)),
        criar_chamado(3, setor="RH", solicitante="Bruno Alves"),
    ]


def test_sem_filtro_devolve_tudo_mais_recentes_primeiro():
    chamados = _base()
    chamados[2] = criar_chamado(3, data_abertura=AGORA - timedelta(hours=1), prazo=AGORA + timedelta(hours=5))
    resultado = aplicar_filtro(chamados, None, AGORA)
    assert [c.numero for c in resultado][0] == 3
    assert len(resultado) == 3


def test_filtra_por_setor_status_prioridade_e_busca():
    chamados = _base()
    assert [c.numero for c in aplicar_filtro(chamados, FiltroChamados(setores=["Financeiro"]), AGORA)] == [1]
    assert len(aplicar_filtro(chamados, FiltroChamados(prioridades=[Prioridade.CRITICA]), AGORA)) == 1
    assert len(aplicar_filtro(chamados, FiltroChamados(status=[Status.CONCLUIDO]), AGORA)) == 0
    assert [c.numero for c in aplicar_filtro(chamados, FiltroChamados(busca="bruno"), AGORA)] == [3]
    assert [c.numero for c in aplicar_filtro(chamados, FiltroChamados(busca="impressora"), AGORA)] == [1]


def test_filtra_sem_responsavel_e_atrasados():
    chamados = _base()
    sem_resp = aplicar_filtro(chamados, FiltroChamados(responsaveis=[SEM_RESPONSAVEL]), AGORA)
    assert [c.numero for c in sem_resp] == [2]
    atrasados = aplicar_filtro(chamados, FiltroChamados(apenas_atrasados=True), AGORA)
    assert [c.numero for c in atrasados] == [2]


def test_filtra_por_periodo_de_abertura():
    antigo = criar_chamado(1, data_abertura=AGORA - timedelta(days=30), prazo=AGORA - timedelta(days=29))
    recente = criar_chamado(2)
    filtro = FiltroChamados(data_inicio=(AGORA - timedelta(days=5)).date(), data_fim=AGORA.date())
    assert [c.numero for c in aplicar_filtro([antigo, recente], filtro, AGORA)] == [2]
