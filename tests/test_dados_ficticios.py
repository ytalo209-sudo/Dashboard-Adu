from __future__ import annotations

from domain.models import Prioridade, Status
from repositories.dados_ficticios import RESPONSAVEIS, gerar_chamados
from repositories.mock_repository import MockChamadoRepository
from tests.fabricas import AGORA


def test_quantidade_e_numeros_unicos():
    chamados = gerar_chamados(qtd=150, agora=AGORA)
    assert len(chamados) == 150
    assert len({c.numero for c in chamados}) == 150


def test_mesma_semente_gera_mesmos_dados():
    a = gerar_chamados(qtd=40, semente=7, agora=AGORA)
    b = gerar_chamados(qtd=40, semente=7, agora=AGORA)
    assert a == b
    assert a != gerar_chamados(qtd=40, semente=8, agora=AGORA)


def test_invariantes_dos_dados():
    for c in gerar_chamados(agora=AGORA):
        assert c.data_abertura <= AGORA
        assert c.prazo > c.data_abertura
        if c.status == Status.CONCLUIDO:
            assert c.data_conclusao is not None and c.data_conclusao <= AGORA
        if c.status != Status.ABERTO:
            assert c.responsavel in RESPONSAVEIS


def test_dados_cobrem_cenarios_do_dashboard():
    chamados = gerar_chamados(agora=AGORA)
    assert {c.status for c in chamados} == set(Status)
    assert any(c.prioridade == Prioridade.CRITICA for c in chamados)
    assert any(c.esta_atrasado(AGORA) for c in chamados)


def test_repositorio_devolve_copias():
    repo = MockChamadoRepository(gerar_chamados(qtd=5, agora=AGORA))
    chamado = repo.obter(1001)
    chamado.titulo = "Alterado fora do repositório"
    assert repo.obter(1001).titulo != "Alterado fora do repositório"
