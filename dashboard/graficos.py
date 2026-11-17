"""Gráficos Plotly. Recebem o DataFrame de chamados e devolvem ``go.Figure``.

Cores: paleta categórica de referência, atribuída em ordem fixa por entidade
(a cor de "Aberto" é sempre a mesma, independente de filtros). Prioridade é ordinal:
uma única família (azul) do claro ao escuro. Grade discreta, fundo transparente
(herda o tema claro/escuro do Streamlit).
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from domain.models import ORDEM_PRIORIDADE, ORDEM_STATUS
from services import indicadores

AZUL = "#2a78d6"
LARANJA = "#eb6834"
GRADE = "rgba(137,135,129,0.25)"
EIXO = "rgba(137,135,129,0.6)"

CORES_STATUS = {
    "Aberto": "#2a78d6",
    "Em andamento": "#eb6834",
    "Pendente": "#1baf7a",
    "Concluído": "#eda100",
}
CORES_PRIORIDADE = {
    "Baixa": "#86b6ef",
    "Média": "#3987e5",
    "Alta": "#1c5cab",
    "Crítica": "#184f95",
}


def _acabamento(fig: go.Figure, titulo: str, altura: int = 320) -> go.Figure:
    fig.update_layout(
        title=dict(text=titulo, x=0, font=dict(size=15)),
        height=altura,
        margin=dict(l=8, r=8, t=48, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif"),
        hoverlabel=dict(font_size=13),
    )
    fig.update_xaxes(title=None, showgrid=False, linecolor=EIXO)
    fig.update_yaxes(title=None, gridcolor=GRADE, zeroline=False)
    return fig


def _barras_horizontais(dados: pd.DataFrame, categoria: str, titulo: str) -> go.Figure:
    dados = dados.sort_values("total")  # a maior barra fica no topo
    fig = px.bar(dados, x="total", y=categoria, orientation="h", text="total")
    fig.update_traces(
        marker_color=AZUL,
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: %{x} chamados<extra></extra>",
    )
    _acabamento(fig, titulo)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)")
    return fig


def chamados_por_setor(df: pd.DataFrame) -> go.Figure:
    return _barras_horizontais(indicadores.contagem_por(df, "setor"), "setor", "Chamados por setor")


def problemas_recorrentes(df: pd.DataFrame, top: int = 8) -> go.Figure:
    return _barras_horizontais(
        indicadores.problemas_recorrentes(df, top), "categoria", "Problemas mais recorrentes"
    )


def _barras_verticais(
    dados: pd.DataFrame, coluna: str, ordem: list[str], cores: dict[str, str], titulo: str
) -> go.Figure:
    fig = px.bar(
        dados,
        x=coluna,
        y="total",
        color=coluna,
        color_discrete_map=cores,
        category_orders={coluna: ordem},
        text="total",
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{x}: %{y} chamados<extra></extra>",
    )
    _acabamento(fig, titulo)
    fig.update_layout(showlegend=False, bargap=0.45)
    fig.update_yaxes(visible=False)
    return fig


def chamados_por_prioridade(df: pd.DataFrame) -> go.Figure:
    dados = indicadores.contagem_por(df, "prioridade", ORDEM_PRIORIDADE)
    return _barras_verticais(dados, "prioridade", ORDEM_PRIORIDADE, CORES_PRIORIDADE, "Chamados por prioridade")


def chamados_por_status(df: pd.DataFrame) -> go.Figure:
    dados = indicadores.contagem_por(df, "status", ORDEM_STATUS)
    return _barras_verticais(dados, "status", ORDEM_STATUS, CORES_STATUS, "Chamados por status")


def evolucao_mensal(df: pd.DataFrame) -> go.Figure:
    dados = indicadores.evolucao_mensal(df)
    fig = go.Figure()
    for coluna, nome, cor in (("abertos", "Abertos", AZUL), ("concluidos", "Concluídos", LARANJA)):
        fig.add_trace(
            go.Scatter(
                x=dados["mes"],
                y=dados[coluna],
                name=nome,
                mode="lines+markers",
                line=dict(color=cor, width=2),
                marker=dict(size=8, color=cor, line=dict(width=2, color="rgba(255,255,255,0.9)")),
            )
        )
    _acabamento(fig, "Evolução de chamados por mês")
    fig.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(type="category")
    return fig


def tempo_medio_atendimento(df: pd.DataFrame) -> go.Figure:
    dados = indicadores.tempo_medio_por_mes(df)
    fig = px.bar(dados, x="mes", y="horas", text="horas")
    fig.update_traces(
        marker_color=AZUL,
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{x}: %{y} h em média<extra></extra>",
    )
    _acabamento(fig, "Tempo médio de atendimento (horas, por mês de conclusão)")
    fig.update_layout(bargap=0.45)
    fig.update_yaxes(visible=False)
    fig.update_xaxes(type="category")
    return fig
