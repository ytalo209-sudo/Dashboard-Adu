"""Cálculo de indicadores sobre um DataFrame de chamados (sem Streamlit nem Plotly)."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from domain.models import SEM_RESPONSAVEL, Chamado, Prioridade, Status

COLUNAS = [
    "numero", "titulo", "descricao", "solicitante", "setor", "categoria", "responsavel",
    "data_abertura", "data_conclusao", "status", "prioridade", "urgencia", "prazo", "atrasado",
]


def para_dataframe(chamados: list[Chamado], agora: datetime) -> pd.DataFrame:
    linhas = [
        {
            "numero": c.numero,
            "titulo": c.titulo,
            "descricao": c.descricao,
            "solicitante": c.solicitante,
            "setor": c.setor,
            "categoria": c.categoria,
            "responsavel": c.responsavel or SEM_RESPONSAVEL,
            "data_abertura": c.data_abertura,
            "data_conclusao": c.data_conclusao,
            "status": c.status.value,
            "prioridade": c.prioridade.value,
            "urgencia": c.urgencia.value,
            "prazo": c.prazo,
            "atrasado": c.esta_atrasado(agora),
        }
        for c in chamados
    ]
    df = pd.DataFrame(linhas, columns=COLUNAS)
    for coluna in ("data_abertura", "data_conclusao", "prazo"):
        df[coluna] = pd.to_datetime(df[coluna])
    df["atrasado"] = df["atrasado"].astype(bool)
    return df


def _horas_de_atendimento(df: pd.DataFrame) -> pd.Series:
    concluidos = df[df["data_conclusao"].notna()]
    return (concluidos["data_conclusao"] - concluidos["data_abertura"]).dt.total_seconds() / 3600


def tempo_medio_horas(df: pd.DataFrame) -> float | None:
    """Média (em horas) entre abertura e conclusão, só de chamados concluídos."""
    horas = _horas_de_atendimento(df)
    return None if horas.empty else round(float(horas.mean()), 1)


def kpis(df: pd.DataFrame) -> dict[str, int | float | None]:
    """Indicadores da página inicial.

    "Críticos" = prioridade Crítica ainda não concluída.
    "Atrasados" = não concluídos com prazo vencido.
    """
    status = df["status"]
    return {
        "total": int(len(df)),
        "abertos": int((status == Status.ABERTO.value).sum()),
        "em_andamento": int((status == Status.EM_ANDAMENTO.value).sum()),
        "pendentes": int((status == Status.PENDENTE.value).sum()),
        "concluidos": int((status == Status.CONCLUIDO.value).sum()),
        "criticos": int(
            ((df["prioridade"] == Prioridade.CRITICA.value) & (status != Status.CONCLUIDO.value)).sum()
        ),
        "atrasados": int(df["atrasado"].sum()),
        "tempo_medio_horas": tempo_medio_horas(df),
    }


def contagem_por(df: pd.DataFrame, coluna: str, ordem: list[str] | None = None) -> pd.DataFrame:
    """Contagem por categoria. Com ``ordem``, mantém todas as categorias (inclusive zeradas)."""
    cont = df[coluna].value_counts()
    if ordem is not None:
        cont = cont.reindex(ordem, fill_value=0)
    return cont.rename_axis(coluna).reset_index(name="total")


def evolucao_mensal(df: pd.DataFrame) -> pd.DataFrame:
    """Chamados abertos e concluídos por mês (colunas: mes, abertos, concluidos)."""
    if df.empty:
        return pd.DataFrame({"mes": [], "abertos": [], "concluidos": []})
    abertos = df["data_abertura"].dt.to_period("M").value_counts()
    concluidos = df["data_conclusao"].dropna().dt.to_period("M").value_counts()
    tabela = pd.DataFrame({"abertos": abertos, "concluidos": concluidos}).fillna(0).astype(int)
    tabela = tabela.sort_index()
    tabela.index = tabela.index.astype(str)
    return tabela.rename_axis("mes").reset_index()


def tempo_medio_por_mes(df: pd.DataFrame) -> pd.DataFrame:
    """Tempo médio de atendimento (horas) por mês de conclusão (colunas: mes, horas)."""
    concluidos = df[df["data_conclusao"].notna()]
    if concluidos.empty:
        return pd.DataFrame({"mes": [], "horas": []})
    horas = _horas_de_atendimento(df)
    mes = concluidos["data_conclusao"].dt.to_period("M")
    media = horas.groupby(mes).mean().round(1).sort_index()
    media.index = media.index.astype(str)
    return media.rename_axis("mes").reset_index(name="horas")


def problemas_recorrentes(df: pd.DataFrame, top: int = 10) -> pd.DataFrame:
    return contagem_por(df, "categoria").head(top)


def resumo_por_responsavel(df: pd.DataFrame) -> pd.DataFrame:
    """Carga por responsável (colunas: responsavel, total, em_aberto, atrasados)."""
    if df.empty:
        return pd.DataFrame({"responsavel": [], "total": [], "em_aberto": [], "atrasados": []})
    nao_concluido = df["status"] != Status.CONCLUIDO.value
    resumo = (
        df.assign(em_aberto=nao_concluido.astype(int), atrasado_int=df["atrasado"].astype(int))
        .groupby("responsavel")
        .agg(total=("numero", "count"), em_aberto=("em_aberto", "sum"), atrasados=("atrasado_int", "sum"))
        .reset_index()
        .sort_values(["atrasados", "em_aberto"], ascending=False)
    )
    return resumo.reset_index(drop=True)
