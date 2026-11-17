"""Exceções da camada de banco. As mensagens nunca incluem credenciais."""
from __future__ import annotations


class DatabaseError(Exception):
    pass


class DatabaseConfigError(DatabaseError):
    """Configuração ausente ou inválida."""


class DatabaseConnectionError(DatabaseError):
    """Falha ao conectar ou executar no banco."""


class DependencyMissingError(DatabaseError):
    """Biblioteca necessária não está instalada."""
