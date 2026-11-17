"""Modelos de domínio validados com Pydantic."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

SEM_RESPONSAVEL = "Sem responsável"


class Status(str, Enum):
    ABERTO = "Aberto"
    EM_ANDAMENTO = "Em andamento"
    PENDENTE = "Pendente"
    CONCLUIDO = "Concluído"


class Prioridade(str, Enum):
    BAIXA = "Baixa"
    MEDIA = "Média"
    ALTA = "Alta"
    CRITICA = "Crítica"


class Urgencia(str, Enum):
    BAIXA = "Baixa"
    MEDIA = "Média"
    ALTA = "Alta"


ORDEM_STATUS = [s.value for s in Status]
ORDEM_PRIORIDADE = [p.value for p in Prioridade]
ORDEM_URGENCIA = [u.value for u in Urgencia]


class Perfil(str, Enum):
    LEITOR = "Leitor"
    ANALISTA = "Analista"
    GESTOR = "Gestor"


class Permissao(str, Enum):
    VISUALIZAR = "visualizar"
    ALTERAR_STATUS = "alterar_status"
    ADICIONAR_OBSERVACAO = "adicionar_observacao"
    ALTERAR_PRIORIDADE = "alterar_prioridade"
    ALTERAR_URGENCIA = "alterar_urgencia"
    ALTERAR_RESPONSAVEL = "alterar_responsavel"
    REABRIR = "reabrir"


class Usuario(BaseModel):
    model_config = ConfigDict(frozen=True)

    login: str = Field(min_length=1)
    nome: str = Field(min_length=1)
    perfil: Perfil


class Chamado(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    numero: int = Field(gt=0)
    titulo: str = Field(min_length=3, max_length=200)
    descricao: str = Field(default="", max_length=4000)
    solicitante: str = Field(min_length=1)
    setor: str = Field(min_length=1)
    categoria: str = Field(min_length=1)
    responsavel: str | None = None
    data_abertura: datetime
    data_conclusao: datetime | None = None
    status: Status = Status.ABERTO
    prioridade: Prioridade = Prioridade.MEDIA
    urgencia: Urgencia = Urgencia.MEDIA
    prazo: datetime

    @model_validator(mode="after")
    def _validar_coerencia(self) -> "Chamado":
        if self.data_conclusao is not None and self.data_conclusao < self.data_abertura:
            raise ValueError("data_conclusao não pode ser anterior à data_abertura.")
        if self.prazo < self.data_abertura:
            raise ValueError("prazo não pode ser anterior à data_abertura.")
        if self.status == Status.CONCLUIDO and self.data_conclusao is None:
            raise ValueError("Chamado concluído exige data_conclusao.")
        if self.status != Status.CONCLUIDO and self.data_conclusao is not None:
            raise ValueError("Somente chamado concluído pode ter data_conclusao.")
        return self

    @property
    def critico(self) -> bool:
        return self.prioridade == Prioridade.CRITICA

    def esta_atrasado(self, agora: datetime) -> bool:
        """Atrasado = ainda não concluído e com o prazo já vencido."""
        return self.status != Status.CONCLUIDO and agora > self.prazo


class HistoricoEntry(BaseModel):
    """Registro de auditoria de uma operação sobre um chamado."""

    model_config = ConfigDict(frozen=True)

    chamado_numero: int
    usuario: str
    data_hora: datetime
    campo: str
    valor_anterior: str | None = None
    valor_novo: str | None = None
    observacao: str | None = None
