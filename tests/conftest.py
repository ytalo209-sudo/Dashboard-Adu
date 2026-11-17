from __future__ import annotations

from datetime import timedelta

import pytest

from domain.models import Status
from repositories.mock_repository import MockChamadoRepository
from services.chamado_service import ChamadoService
from tests.fabricas import AGORA, Relogio, criar_chamado

EQUIPE = ["Carlos Mendes", "Juliana Prado"]


@pytest.fixture
def relogio() -> Relogio:
    return Relogio()


@pytest.fixture
def repo() -> MockChamadoRepository:
    """#1 aberto com responsável | #2 concluído | #3 aberto SEM responsável."""
    return MockChamadoRepository(
        [
            criar_chamado(1),
            criar_chamado(
                2,
                status=Status.CONCLUIDO,
                data_conclusao=AGORA - timedelta(hours=2),
            ),
            criar_chamado(3, responsavel=None),
        ],
        responsaveis=EQUIPE,
    )


@pytest.fixture
def servico(repo: MockChamadoRepository, relogio: Relogio) -> ChamadoService:
    return ChamadoService(repo, relogio=relogio)
