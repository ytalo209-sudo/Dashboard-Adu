"""Componentes de interface Streamlit: sessão simulada, filtros, cards, tabela e ações."""
from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from domain.exceptions import ConfirmacaoNecessariaError, ServiceError
from domain.filtros import FiltroChamados
from domain.models import (
    ORDEM_PRIORIDADE,
    ORDEM_STATUS,
    ORDEM_URGENCIA,
    SEM_RESPONSAVEL,
    Chamado,
    Permissao,
    Prioridade,
    Status,
    Urgencia,
    Usuario,
)
from services.chamado_service import ChamadoService
from services.permissions import tem_permissao

FORMATO_DATA_HORA = "DD/MM/YYYY HH:mm"


# --------------------------------------------------------------- barra lateral
def seletor_usuario(usuarios: list[Usuario]) -> Usuario:
    st.sidebar.header("Sessão simulada")
    por_nome = {u.nome: u for u in usuarios}
    escolhido = st.sidebar.selectbox("Usuário", list(por_nome))
    usuario = por_nome[escolhido]
    st.sidebar.caption(
        f"Perfil: {usuario.perfil.value}. Em produção, o usuário virá do login corporativo."
    )
    return usuario


def filtros_sidebar(servico: ChamadoService) -> FiltroChamados:
    st.sidebar.header("Filtros")
    hoje = servico.agora().date()
    periodo = st.sidebar.date_input(
        "Período de abertura",
        value=(hoje - timedelta(days=180), hoje),
        format="DD/MM/YYYY",
    )
    inicio: date | None = None
    fim: date | None = None
    if isinstance(periodo, (tuple, list)) and len(periodo) == 2:  # 1 data = usuário ainda escolhendo
        inicio, fim = periodo

    setores = st.sidebar.multiselect("Setor", servico.setores())
    responsaveis = st.sidebar.multiselect("Responsável", [SEM_RESPONSAVEL] + servico.responsaveis())
    status = st.sidebar.multiselect("Status", ORDEM_STATUS)
    prioridades = st.sidebar.multiselect("Prioridade", ORDEM_PRIORIDADE)
    atrasados = st.sidebar.checkbox("Somente atrasados")
    busca = st.sidebar.text_input("Buscar (nº, título, solicitante)")

    return FiltroChamados(
        data_inicio=inicio,
        data_fim=fim,
        setores=setores,
        responsaveis=responsaveis,
        status=[Status(s) for s in status],
        prioridades=[Prioridade(p) for p in prioridades],
        apenas_atrasados=atrasados,
        busca=busca,
    )


# ------------------------------------------------------------------- cartões
def cartoes_kpi(k: dict) -> None:
    tempo = k["tempo_medio_horas"]
    linhas = [
        [("Total de chamados", k["total"]), ("Abertos", k["abertos"]),
         ("Em andamento", k["em_andamento"]), ("Pendentes", k["pendentes"])],
        [("Concluídos", k["concluidos"]), ("Críticos (não concluídos)", k["criticos"]),
         ("Atrasados", k["atrasados"]),
         ("Tempo médio de atendimento", "—" if tempo is None else f"{tempo} h")],
    ]
    for linha in linhas:
        for coluna, (rotulo, valor) in zip(st.columns(len(linha)), linha):
            coluna.metric(rotulo, valor, border=True)


# -------------------------------------------------------------------- tabela
def tabela_chamados(df: pd.DataFrame) -> None:
    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        column_order=[
            "numero", "titulo", "descricao", "solicitante", "setor", "responsavel",
            "data_abertura", "status", "prioridade", "urgencia", "prazo", "atrasado",
        ],
        column_config={
            "numero": st.column_config.NumberColumn("Nº", format="%d"),
            "titulo": st.column_config.TextColumn("Título"),
            "descricao": st.column_config.TextColumn("Descrição", width="large"),
            "solicitante": st.column_config.TextColumn("Solicitante"),
            "setor": st.column_config.TextColumn("Setor"),
            "responsavel": st.column_config.TextColumn("Responsável"),
            "data_abertura": st.column_config.DatetimeColumn("Abertura", format=FORMATO_DATA_HORA),
            "status": st.column_config.TextColumn("Status"),
            "prioridade": st.column_config.TextColumn("Prioridade"),
            "urgencia": st.column_config.TextColumn("Urgência"),
            "prazo": st.column_config.DatetimeColumn("Prazo", format=FORMATO_DATA_HORA),
            "atrasado": st.column_config.CheckboxColumn("Atrasado"),
        },
    )


# ------------------------------------------------------------ detalhe e ações
def _executar(acao: Callable[[], object], mensagem_ok: str) -> None:
    try:
        acao()
    except ConfirmacaoNecessariaError as exc:
        st.warning(f"{exc} Marque a caixa de confirmação e aplique novamente.")
    except ServiceError as exc:
        st.error(str(exc))
    else:
        st.session_state["flash"] = mensagem_ok
        st.rerun()


def _sem_permissao(rotulo: str) -> None:
    st.markdown(f"**{rotulo}**")
    st.caption(f"Seu perfil não permite alterar: {rotulo.lower()}.")


def _form_prioridade(servico: ChamadoService, usuario: Usuario, c: Chamado) -> None:
    if not tem_permissao(usuario, Permissao.ALTERAR_PRIORIDADE):
        return _sem_permissao("Prioridade")
    with st.form(f"prioridade_{c.numero}"):
        st.markdown("**Prioridade**")
        nova = st.selectbox("Nova prioridade", ORDEM_PRIORIDADE, index=ORDEM_PRIORIDADE.index(c.prioridade.value))
        confirmar = st.checkbox("Confirmo alteração crítica (envolve prioridade Crítica)")
        enviar = st.form_submit_button("Aplicar prioridade")
    if enviar:
        _executar(
            lambda: servico.alterar_prioridade(usuario, c.numero, Prioridade(nova), confirmar=confirmar),
            "Prioridade atualizada.",
        )


def _form_urgencia(servico: ChamadoService, usuario: Usuario, c: Chamado) -> None:
    if not tem_permissao(usuario, Permissao.ALTERAR_URGENCIA):
        return _sem_permissao("Urgência")
    with st.form(f"urgencia_{c.numero}"):
        st.markdown("**Urgência**")
        nova = st.selectbox("Nova urgência", ORDEM_URGENCIA, index=ORDEM_URGENCIA.index(c.urgencia.value))
        enviar = st.form_submit_button("Aplicar urgência")
    if enviar:
        _executar(lambda: servico.alterar_urgencia(usuario, c.numero, Urgencia(nova)), "Urgência atualizada.")


def _form_responsavel(servico: ChamadoService, usuario: Usuario, c: Chamado) -> None:
    if not tem_permissao(usuario, Permissao.ALTERAR_RESPONSAVEL):
        return _sem_permissao("Responsável")
    opcoes = [SEM_RESPONSAVEL] + servico.responsaveis()
    atual = c.responsavel or SEM_RESPONSAVEL
    with st.form(f"responsavel_{c.numero}"):
        st.markdown("**Responsável**")
        novo = st.selectbox("Novo responsável", opcoes, index=opcoes.index(atual) if atual in opcoes else 0)
        enviar = st.form_submit_button("Aplicar responsável")
    if enviar:
        _executar(
            lambda: servico.alterar_responsavel(usuario, c.numero, None if novo == SEM_RESPONSAVEL else novo),
            "Responsável atualizado.",
        )


def _form_status(servico: ChamadoService, usuario: Usuario, c: Chamado) -> None:
    if not tem_permissao(usuario, Permissao.ALTERAR_STATUS):
        return _sem_permissao("Status")
    with st.form(f"status_{c.numero}"):
        st.markdown("**Status**")
        novo = st.selectbox("Novo status", ORDEM_STATUS, index=ORDEM_STATUS.index(c.status.value))
        confirmar = st.checkbox("Confirmo concluir ou reabrir este chamado")
        enviar = st.form_submit_button("Aplicar status")
    if enviar:
        _executar(
            lambda: servico.atualizar_status(usuario, c.numero, Status(novo), confirmar=confirmar),
            "Status atualizado.",
        )


def _form_observacao(servico: ChamadoService, usuario: Usuario, c: Chamado) -> None:
    if not tem_permissao(usuario, Permissao.ADICIONAR_OBSERVACAO):
        return _sem_permissao("Observações")
    with st.form(f"observacao_{c.numero}", clear_on_submit=True):
        st.markdown("**Adicionar observação**")
        texto = st.text_area("Observação", max_chars=1000)
        enviar = st.form_submit_button("Registrar observação")
    if enviar:
        _executar(lambda: servico.adicionar_observacao(usuario, c.numero, texto), "Observação registrada.")


def painel_detalhe(servico: ChamadoService, usuario: Usuario, chamados: list[Chamado]) -> None:
    flash = st.session_state.pop("flash", None)
    if flash:
        st.success(flash)
    if not chamados:
        st.info("Nenhum chamado para os filtros selecionados.")
        return

    rotulos = {c.numero: f"#{c.numero} · {c.titulo} ({c.setor})" for c in chamados}
    numero = st.selectbox("Chamado", list(rotulos), format_func=lambda n: rotulos[n])

    c = servico.obter(usuario, numero)
    agora = servico.agora()
    st.subheader(f"#{c.numero} · {c.titulo}")
    st.write(c.descricao or "_Sem descrição._")
    st.caption(
        f"Solicitante: {c.solicitante} · Setor: {c.setor} · Categoria: {c.categoria} · "
        f"Responsável: {c.responsavel or SEM_RESPONSAVEL} · Aberto em {c.data_abertura:%d/%m/%Y %H:%M}"
    )
    if c.esta_atrasado(agora):
        st.warning(f"Chamado atrasado: o prazo venceu em {c.prazo:%d/%m/%Y %H:%M}.")

    colunas = st.columns(4)
    colunas[0].metric("Status", c.status.value)
    colunas[1].metric("Prioridade", c.prioridade.value)
    colunas[2].metric("Urgência", c.urgencia.value)
    colunas[3].metric("Prazo", f"{c.prazo:%d/%m/%Y %H:%M}")

    st.divider()
    st.subheader("Ações")
    esquerda, direita = st.columns(2)
    with esquerda:
        _form_prioridade(servico, usuario, c)
        _form_urgencia(servico, usuario, c)
    with direita:
        _form_responsavel(servico, usuario, c)
        _form_status(servico, usuario, c)
    _form_observacao(servico, usuario, c)

    st.divider()
    historico_chamado(servico, usuario, c.numero)


def historico_chamado(servico: ChamadoService, usuario: Usuario, numero: int) -> None:
    st.subheader("Histórico de modificações")
    entradas = servico.historico(usuario, numero)
    if not entradas:
        st.caption("Nenhuma modificação registrada para este chamado.")
        return
    tabela = pd.DataFrame(
        [
            {
                "Data/hora": e.data_hora,
                "Usuário": e.usuario,
                "Campo": e.campo,
                "De": e.valor_anterior,
                "Para": e.valor_novo,
                "Observação": e.observacao,
            }
            for e in entradas
        ]
    )
    st.dataframe(
        tabela,
        hide_index=True,
        width="stretch",
        column_config={"Data/hora": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm:ss")},
    )
