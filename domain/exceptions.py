"""Exceções de negócio. A interface captura ServiceError e mostra a mensagem ao usuário."""
from __future__ import annotations


class ServiceError(Exception):
    """Base para erros esperados da camada de serviços."""


class PermissaoNegadaError(ServiceError):
    pass


class ChamadoNaoEncontradoError(ServiceError):
    def __init__(self, numero: int) -> None:
        super().__init__(f"Chamado #{numero} não encontrado.")
        self.numero = numero


class RegraDeNegocioError(ServiceError):
    pass


class ConfirmacaoNecessariaError(ServiceError):
    """A operação é crítica e precisa de confirmação explícita do usuário."""
