"""Regras de negócio sobre chamados.

Toda operação passa por: permissão -> existência -> regras -> confirmação (se crítica)
-> gravação -> registro de auditoria (quem, quando, campo, valor anterior e novo).
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any

from domain.exceptions import (
    ChamadoNaoEncontradoError,
    ConfirmacaoNecessariaError,
    RegraDeNegocioError,
)
from domain.filtros import FiltroChamados
from domain.models import (
    Chamado,
    HistoricoEntry,
    Permissao,
    Prioridade,
    Status,
    Urgencia,
    Usuario,
)
from repositories.base import ChamadoRepository
from services.permissions import exigir_permissao

logger = logging.getLogger("chamados.auditoria")

TAMANHO_MAX_OBSERVACAO = 1000


def _texto(valor: Any) -> str:
    if valor is None:
        return "(vazio)"
    return valor.value if isinstance(valor, Enum) else str(valor)


class ChamadoService:
    def __init__(
        self,
        repositorio: ChamadoRepository,
        relogio: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._repo = repositorio
        self._relogio = relogio

    def agora(self) -> datetime:
        return self._relogio()

    # ----------------------------------------------------------- consultas
    def listar(self, usuario: Usuario, filtro: FiltroChamados | None = None) -> list[Chamado]:
        exigir_permissao(usuario, Permissao.VISUALIZAR)
        return self._repo.listar(filtro, agora=self.agora())

    def obter(self, usuario: Usuario, numero: int) -> Chamado:
        exigir_permissao(usuario, Permissao.VISUALIZAR)
        return self._buscar(numero)

    def historico(self, usuario: Usuario, numero: int) -> list[HistoricoEntry]:
        exigir_permissao(usuario, Permissao.VISUALIZAR)
        self._buscar(numero)
        return self._repo.historico(numero)

    def setores(self) -> list[str]:
        return self._repo.listar_setores()

    def responsaveis(self) -> list[str]:
        return self._repo.listar_responsaveis()

    # ------------------------------------------------------------ operações
    def alterar_prioridade(
        self, usuario: Usuario, numero: int, nova: Prioridade, confirmar: bool = False
    ) -> Chamado:
        nova = Prioridade(nova)

        def exige(c: Chamado) -> str | None:
            if nova == Prioridade.CRITICA:
                return "Elevar a prioridade para Crítica é uma alteração crítica e exige confirmação."
            if c.prioridade == Prioridade.CRITICA:
                return "Reduzir a prioridade de um chamado Crítico exige confirmação."
            return None

        return self._alterar(
            usuario, numero, Permissao.ALTERAR_PRIORIDADE, "Prioridade", "prioridade",
            nova, confirmar, exige_confirmacao=exige,
        )

    def alterar_urgencia(self, usuario: Usuario, numero: int, nova: Urgencia) -> Chamado:
        return self._alterar(
            usuario, numero, Permissao.ALTERAR_URGENCIA, "Urgência", "urgencia",
            Urgencia(nova), False,
        )

    def alterar_responsavel(self, usuario: Usuario, numero: int, novo: str | None) -> Chamado:
        novo = novo or None

        def regra(_: Chamado) -> None:
            if novo is not None and novo not in self._repo.listar_responsaveis():
                raise RegraDeNegocioError(f"Responsável '{novo}' não pertence à equipe de TI.")

        return self._alterar(
            usuario, numero, Permissao.ALTERAR_RESPONSAVEL, "Responsável", "responsavel",
            novo, False, regra=regra,
        )

    def atualizar_status(
        self, usuario: Usuario, numero: int, novo: Status, confirmar: bool = False
    ) -> Chamado:
        novo = Status(novo)

        def regra(c: Chamado) -> None:
            if c.status == Status.CONCLUIDO:
                exigir_permissao(usuario, Permissao.REABRIR)
                if novo not in (Status.ABERTO, Status.EM_ANDAMENTO):
                    raise RegraDeNegocioError(
                        "Um chamado concluído só pode ser reaberto como Aberto ou Em andamento."
                    )
            elif novo == Status.CONCLUIDO and c.responsavel is None:
                raise RegraDeNegocioError("Atribua um responsável antes de concluir o chamado.")

        def exige(c: Chamado) -> str | None:
            if novo == Status.CONCLUIDO:
                return "Concluir o chamado exige confirmação."
            if c.status == Status.CONCLUIDO:
                return "Reabrir um chamado concluído exige confirmação."
            return None

        def efeitos(c: Chamado, agora: datetime) -> dict[str, Any]:
            if novo == Status.CONCLUIDO:
                return {"data_conclusao": agora}
            if c.status == Status.CONCLUIDO:
                return {"data_conclusao": None}
            return {}

        return self._alterar(
            usuario, numero, Permissao.ALTERAR_STATUS, "Status", "status",
            novo, confirmar, regra=regra, exige_confirmacao=exige, efeitos=efeitos,
        )

    def adicionar_observacao(self, usuario: Usuario, numero: int, texto: str) -> HistoricoEntry:
        exigir_permissao(usuario, Permissao.ADICIONAR_OBSERVACAO)
        texto = (texto or "").strip()
        if not texto:
            raise RegraDeNegocioError("A observação não pode ser vazia.")
        if len(texto) > TAMANHO_MAX_OBSERVACAO:
            raise RegraDeNegocioError(
                f"A observação excede {TAMANHO_MAX_OBSERVACAO} caracteres."
            )
        self._buscar(numero)
        entrada = HistoricoEntry(
            chamado_numero=numero,
            usuario=usuario.login,
            data_hora=self.agora(),
            campo="Observação",
            observacao=texto,
        )
        self._repo.adicionar_historico(entrada)
        logger.info("auditoria usuario=%s chamado=%s campo=Observação", usuario.login, numero)
        return entrada

    # ------------------------------------------------------------- internos
    def _buscar(self, numero: int) -> Chamado:
        chamado = self._repo.obter(numero)
        if chamado is None:
            raise ChamadoNaoEncontradoError(numero)
        return chamado

    def _alterar(
        self,
        usuario: Usuario,
        numero: int,
        permissao: Permissao,
        rotulo: str,
        atributo: str,
        novo: Any,
        confirmar: bool,
        *,
        regra: Callable[[Chamado], None] | None = None,
        exige_confirmacao: Callable[[Chamado], str | None] | None = None,
        efeitos: Callable[[Chamado, datetime], dict[str, Any]] | None = None,
    ) -> Chamado:
        exigir_permissao(usuario, permissao)
        atual = self._buscar(numero)
        anterior = getattr(atual, atributo)

        if novo == anterior:
            raise RegraDeNegocioError(f"{rotulo} já é '{_texto(anterior)}'.")
        if atual.status == Status.CONCLUIDO and atributo != "status":
            raise RegraDeNegocioError(
                "Chamado concluído não pode ser alterado. Reabra o chamado primeiro."
            )
        if regra:
            regra(atual)
        if exige_confirmacao and not confirmar:
            motivo = exige_confirmacao(atual)
            if motivo:
                raise ConfirmacaoNecessariaError(motivo)

        agora = self.agora()
        mudancas: dict[str, Any] = {atributo: novo}
        if efeitos:
            mudancas.update(efeitos(atual, agora))

        # Revalida o modelo completo (coerência de datas, status etc.)
        atualizado = Chamado(**{**atual.model_dump(), **mudancas})
        self._repo.salvar(atualizado)
        self._repo.adicionar_historico(
            HistoricoEntry(
                chamado_numero=numero,
                usuario=usuario.login,
                data_hora=agora,
                campo=rotulo,
                valor_anterior=_texto(anterior),
                valor_novo=_texto(novo),
            )
        )
        logger.info(
            "auditoria usuario=%s chamado=%s campo=%s de=%s para=%s",
            usuario.login, numero, rotulo, _texto(anterior), _texto(novo),
        )
        return atualizado
