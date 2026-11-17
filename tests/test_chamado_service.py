from __future__ import annotations

import pytest

from domain.exceptions import (
    ChamadoNaoEncontradoError,
    ConfirmacaoNecessariaError,
    PermissaoNegadaError,
    RegraDeNegocioError,
)
from domain.models import Prioridade, Status, Urgencia
from tests.fabricas import ANALISTA, GESTOR, LEITOR


def test_leitor_consulta_mas_nao_altera(servico):
    assert servico.obter(LEITOR, 1).numero == 1
    with pytest.raises(PermissaoNegadaError):
        servico.alterar_urgencia(LEITOR, 1, Urgencia.ALTA)
    with pytest.raises(PermissaoNegadaError):
        servico.adicionar_observacao(LEITOR, 1, "teste")


def test_analista_altera_status_mas_nao_prioridade(servico):
    assert servico.atualizar_status(ANALISTA, 1, Status.EM_ANDAMENTO).status == Status.EM_ANDAMENTO
    with pytest.raises(PermissaoNegadaError):
        servico.alterar_prioridade(ANALISTA, 1, Prioridade.ALTA)
    with pytest.raises(PermissaoNegadaError):
        servico.alterar_responsavel(ANALISTA, 1, "Juliana Prado")


def test_alteracao_gera_registro_de_auditoria(servico, relogio):
    servico.alterar_urgencia(GESTOR, 1, Urgencia.ALTA)
    entrada = servico.historico(GESTOR, 1)[0]
    assert entrada.campo == "Urgência"
    assert entrada.valor_anterior == "Média"
    assert entrada.valor_novo == "Alta"
    assert entrada.usuario == "gestor"
    assert entrada.data_hora == relogio()


def test_historico_vem_do_mais_recente_para_o_mais_antigo(servico, relogio):
    servico.alterar_urgencia(GESTOR, 1, Urgencia.ALTA)
    relogio.avancar(minutes=5)
    servico.adicionar_observacao(GESTOR, 1, "Aguardando peça.")
    campos = [e.campo for e in servico.historico(GESTOR, 1)]
    assert campos == ["Observação", "Urgência"]


def test_prioridade_critica_exige_confirmacao(servico, repo):
    with pytest.raises(ConfirmacaoNecessariaError):
        servico.alterar_prioridade(GESTOR, 1, Prioridade.CRITICA)
    assert repo.obter(1).prioridade == Prioridade.MEDIA
    assert repo.historico(1) == []

    servico.alterar_prioridade(GESTOR, 1, Prioridade.CRITICA, confirmar=True)
    assert repo.obter(1).prioridade == Prioridade.CRITICA

    with pytest.raises(ConfirmacaoNecessariaError):  # reduzir também é crítico
        servico.alterar_prioridade(GESTOR, 1, Prioridade.ALTA)


def test_nao_altera_para_o_mesmo_valor(servico):
    with pytest.raises(RegraDeNegocioError):
        servico.alterar_urgencia(GESTOR, 1, Urgencia.MEDIA)


def test_responsavel_precisa_ser_da_equipe(servico, repo):
    with pytest.raises(RegraDeNegocioError):
        servico.alterar_responsavel(GESTOR, 1, "Fulano de Tal")
    servico.alterar_responsavel(GESTOR, 1, "Juliana Prado")
    assert repo.obter(1).responsavel == "Juliana Prado"
    servico.alterar_responsavel(GESTOR, 1, None)
    assert repo.obter(1).responsavel is None


def test_nao_conclui_sem_responsavel(servico):
    with pytest.raises(RegraDeNegocioError, match="responsável"):
        servico.atualizar_status(GESTOR, 3, Status.CONCLUIDO, confirmar=True)


def test_concluir_exige_confirmacao_e_registra_data(servico, repo, relogio):
    with pytest.raises(ConfirmacaoNecessariaError):
        servico.atualizar_status(GESTOR, 1, Status.CONCLUIDO)
    servico.atualizar_status(GESTOR, 1, Status.CONCLUIDO, confirmar=True)
    chamado = repo.obter(1)
    assert chamado.status == Status.CONCLUIDO
    assert chamado.data_conclusao == relogio()


def test_chamado_concluido_nao_aceita_outras_alteracoes(servico):
    with pytest.raises(RegraDeNegocioError, match="concluído"):
        servico.alterar_prioridade(GESTOR, 2, Prioridade.ALTA)


def test_reabrir_exige_perfil_e_confirmacao(servico, repo):
    with pytest.raises(PermissaoNegadaError):
        servico.atualizar_status(ANALISTA, 2, Status.ABERTO, confirmar=True)
    with pytest.raises(ConfirmacaoNecessariaError):
        servico.atualizar_status(GESTOR, 2, Status.ABERTO)
    with pytest.raises(RegraDeNegocioError):
        servico.atualizar_status(GESTOR, 2, Status.PENDENTE, confirmar=True)

    servico.atualizar_status(GESTOR, 2, Status.ABERTO, confirmar=True)
    reaberto = repo.obter(2)
    assert reaberto.status == Status.ABERTO
    assert reaberto.data_conclusao is None


def test_observacao_valida_e_limites(servico):
    with pytest.raises(RegraDeNegocioError):
        servico.adicionar_observacao(ANALISTA, 1, "   ")
    with pytest.raises(RegraDeNegocioError):
        servico.adicionar_observacao(ANALISTA, 1, "x" * 1001)
    entrada = servico.adicionar_observacao(ANALISTA, 1, "  Cliente avisado.  ")
    assert entrada.observacao == "Cliente avisado."


def test_chamado_inexistente(servico):
    with pytest.raises(ChamadoNaoEncontradoError):
        servico.obter(GESTOR, 999)
    with pytest.raises(ChamadoNaoEncontradoError):
        servico.alterar_urgencia(GESTOR, 999, Urgencia.ALTA)


def test_listar_aplica_filtro(servico):
    from domain.filtros import FiltroChamados

    resultado = servico.listar(LEITOR, FiltroChamados(status=[Status.CONCLUIDO]))
    assert [c.numero for c in resultado] == [2]
