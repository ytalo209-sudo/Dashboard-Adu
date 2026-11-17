"""Aplicação Streamlit: monta página, abas e liga interface aos serviços."""
from __future__ import annotations

import logging

import streamlit as st

from config.settings import get_settings
from dashboard import componentes, graficos
from domain.exceptions import ServiceError
from domain.models import Perfil, Usuario
from repositories.mock_repository import MockChamadoRepository
from services import indicadores
from services.chamado_service import ChamadoService

# Usuários FICTÍCIOS para testar permissões. Serão substituídos pelo login corporativo.
USUARIOS_SIMULADOS = [
    Usuario(login="gestora.ana", nome="Ana Lima (Gestora)", perfil=Perfil.GESTOR),
    Usuario(login="analista.carlos", nome="Carlos Mendes (Analista)", perfil=Perfil.ANALISTA),
    Usuario(login="leitor.leo", nome="Leonardo Reis (Leitor)", perfil=Perfil.LEITOR),
]


@st.cache_resource
def _criar_servico() -> ChamadoService:
    """Um único serviço/repositório por processo (preserva as alterações entre reruns)."""
    return ChamadoService(MockChamadoRepository())


def main() -> None:
    st.set_page_config(page_title="Gestão de Chamados de TI", layout="wide")
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    st.title("Gestão de Chamados de TI")
    if settings.data_source != "simulado":
        st.error(
            f"DATA_SOURCE='{settings.data_source}' ainda não está implementado. "
            "Use DATA_SOURCE=simulado (ver README, etapa 2)."
        )
        st.stop()
    st.caption("Modo simulado: dados fictícios em memória, sem conexão com o banco de produção.")

    servico = _criar_servico()
    usuario = componentes.seletor_usuario(USUARIOS_SIMULADOS)
    filtro = componentes.filtros_sidebar(servico)

    try:
        chamados = servico.listar(usuario, filtro)
    except ServiceError as exc:
        st.error(str(exc))
        st.stop()

    agora = servico.agora()
    df = indicadores.para_dataframe(chamados, agora)

    aba_geral, aba_tabela, aba_detalhe, aba_relatorios = st.tabs(
        ["Visão geral", "Chamados", "Detalhe e ações", "Relatórios"]
    )

    with aba_geral:
        componentes.cartoes_kpi(indicadores.kpis(df))
        if df.empty:
            st.info("Nenhum chamado para os filtros selecionados.")
        else:
            c1, c2 = st.columns(2)
            c1.plotly_chart(graficos.chamados_por_setor(df), width="stretch", key="geral_setor")
            c2.plotly_chart(graficos.chamados_por_prioridade(df), width="stretch", key="geral_prioridade")
            c3, c4 = st.columns(2)
            c3.plotly_chart(graficos.chamados_por_status(df), width="stretch", key="geral_status")
            c4.plotly_chart(graficos.evolucao_mensal(df), width="stretch", key="geral_evolucao")
            st.plotly_chart(graficos.tempo_medio_atendimento(df), width="stretch", key="geral_tempo_medio")

    with aba_tabela:
        st.caption(f"{len(df)} chamado(s) encontrados.")
        componentes.tabela_chamados(df)

    with aba_detalhe:
        componentes.painel_detalhe(servico, usuario, chamados)

    with aba_relatorios:
        if df.empty:
            st.info("Nenhum chamado para os filtros selecionados.")
        else:
            c1, c2 = st.columns(2)
            c1.plotly_chart(graficos.problemas_recorrentes(df), width="stretch", key="rel_problemas")
            c2.plotly_chart(graficos.chamados_por_setor(df), width="stretch", key="rel_setor")
            st.subheader("Carga por responsável")
            st.dataframe(
                indicadores.resumo_por_responsavel(df),
                hide_index=True,
                width="stretch",
                column_config={
                    "responsavel": st.column_config.TextColumn("Responsável"),
                    "total": st.column_config.NumberColumn("Chamados"),
                    "em_aberto": st.column_config.NumberColumn("Não concluídos"),
                    "atrasados": st.column_config.NumberColumn("Atrasados"),
                },
            )
            st.download_button(
                "Baixar chamados filtrados (CSV)",
                data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"chamados_{agora:%Y%m%d}.csv",
                mime="text/csv",
            )
