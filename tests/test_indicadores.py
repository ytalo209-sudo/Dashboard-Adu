from __future__ import annotations

from datetime import datetime

from domain.models import ORDEM_PRIORIDADE, Prioridade, Status
from services import indicadores
from tests.fabricas import AGORA, criar_chamado


def _chamados():
    return [
        # #1 aberto, crítico, atrasado
        criar_chamado(1, categoria="Impressora", prioridade=Prioridade.CRITICA,
                      data_abertura=datetime(2026, 11, 10, 8), prazo=datetime(2026, 11, 12, 8)),
        # #2 em andamento, no prazo
        criar_chamado(2, categoria="Impressora", prioridade=Prioridade.ALTA, status=Status.EM_ANDAMENTO,
                      data_abertura=datetime(2026, 11, 15, 9), prazo=datetime(2026, 11, 20, 9)),
        # #3 pendente, atrasado
        criar_chamado(3, categoria="Impressora", prioridade=Prioridade.BAIXA, status=Status.PENDENTE,
                      data_abertura=datetime(2026, 11, 5, 8), prazo=datetime(2026, 11, 8, 8)),
        # #4 concluído em 4 h (outubro)
        criar_chamado(4, categoria="E-mail", prioridade=Prioridade.MEDIA, status=Status.CONCLUIDO,
                      data_abertura=datetime(2026, 10, 1, 10), data_conclusao=datetime(2026, 10, 1, 14),
                      prazo=datetime(2026, 10, 2, 10)),
        # #5 concluído em 2 h (novembro)
        criar_chamado(5, categoria="E-mail", prioridade=Prioridade.MEDIA, status=Status.CONCLUIDO,
                      data_abertura=datetime(2026, 11, 2, 8), data_conclusao=datetime(2026, 11, 2, 10),
                      prazo=datetime(2026, 11, 3, 8)),
    ]


def _df():
    return indicadores.para_dataframe(_chamados(), AGORA)


def test_kpis():
    k = indicadores.kpis(_df())
    assert k["total"] == 5
    assert k["abertos"] == 1
    assert k["em_andamento"] == 1
    assert k["pendentes"] == 1
    assert k["concluidos"] == 2
    assert k["criticos"] == 1
    assert k["atrasados"] == 2
    assert k["tempo_medio_horas"] == 3.0


def test_contagem_por_prioridade_mantem_categorias_zeradas():
    df = _df().iloc[:2]  # só Crítica e Alta
    tabela = indicadores.contagem_por(df, "prioridade", ORDEM_PRIORIDADE)
    assert list(tabela["prioridade"]) == ORDEM_PRIORIDADE
    assert list(tabela["total"]) == [0, 0, 1, 1]


def test_evolucao_mensal():
    tabela = indicadores.evolucao_mensal(_df())
    assert list(tabela["mes"]) == ["2026-10", "2026-11"]
    assert list(tabela["abertos"]) == [1, 4]
    assert list(tabela["concluidos"]) == [1, 1]


def test_tempo_medio_por_mes():
    tabela = indicadores.tempo_medio_por_mes(_df())
    assert list(tabela["mes"]) == ["2026-10", "2026-11"]
    assert list(tabela["horas"]) == [4.0, 2.0]


def test_problemas_recorrentes():
    tabela = indicadores.problemas_recorrentes(_df(), top=1)
    assert list(tabela["categoria"]) == ["Impressora"]
    assert list(tabela["total"]) == [3]


def test_resumo_por_responsavel():
    resumo = indicadores.resumo_por_responsavel(_df())
    linha = resumo.iloc[0]
    assert linha["responsavel"] == "Carlos Mendes"
    assert linha["total"] == 5
    assert linha["em_aberto"] == 3
    assert linha["atrasados"] == 2


def test_dataframe_vazio_nao_quebra():
    df = indicadores.para_dataframe([], AGORA)
    k = indicadores.kpis(df)
    assert k["total"] == 0 and k["atrasados"] == 0 and k["tempo_medio_horas"] is None
    assert indicadores.evolucao_mensal(df).empty
    assert indicadores.tempo_medio_por_mes(df).empty
    assert list(indicadores.contagem_por(df, "prioridade", ORDEM_PRIORIDADE)["total"]) == [0, 0, 0, 0]
    assert indicadores.resumo_por_responsavel(df).empty
