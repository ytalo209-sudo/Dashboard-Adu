"""Controle de acesso por perfil (princípio do menor privilégio)."""
from __future__ import annotations

from domain.exceptions import PermissaoNegadaError
from domain.models import Perfil, Permissao, Usuario

PERMISSOES_POR_PERFIL: dict[Perfil, frozenset[Permissao]] = {
    Perfil.LEITOR: frozenset({Permissao.VISUALIZAR}),
    Perfil.ANALISTA: frozenset(
        {Permissao.VISUALIZAR, Permissao.ALTERAR_STATUS, Permissao.ADICIONAR_OBSERVACAO}
    ),
    Perfil.GESTOR: frozenset(Permissao),
}


def tem_permissao(usuario: Usuario, permissao: Permissao) -> bool:
    return permissao in PERMISSOES_POR_PERFIL.get(usuario.perfil, frozenset())


def exigir_permissao(usuario: Usuario, permissao: Permissao) -> None:
    if not tem_permissao(usuario, permissao):
        raise PermissaoNegadaError(
            f"O perfil {usuario.perfil.value} não tem permissão para esta operação."
        )
