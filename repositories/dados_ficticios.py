"""Gerador determinístico de chamados FICTÍCIOS (nomes e textos inventados)."""
from __future__ import annotations

import random
from datetime import datetime, timedelta

from domain.models import Chamado, Prioridade, Status, Urgencia

SETORES = ["Financeiro", "RH", "Comercial", "Logística", "Jurídico", "Produção", "Marketing", "Diretoria"]
PESOS_SETORES = [18, 8, 20, 10, 5, 14, 10, 5]

RESPONSAVEIS = ["Carlos Mendes", "Juliana Prado", "Rafael Souza", "Mariana Lima", "Eduardo Costa"]

SOLICITANTES = [
    "Ana Ribeiro", "Bruno Alves", "Camila Torres", "Diego Martins", "Elisa Nogueira",
    "Fábio Cardoso", "Gabriela Rocha", "Henrique Dias", "Isabela Freitas", "João Barros",
    "Karen Teixeira", "Lucas Pinto", "Marta Gomes", "Nelson Vieira",
]

# categoria -> lista de (título, descrição). A categoria alimenta "problemas recorrentes".
CATEGORIAS: dict[str, list[tuple[str, str]]] = {
    "Senha / acesso": [
        ("Não consigo acessar minha conta", "Usuário bloqueado após várias tentativas de login."),
        ("Redefinição de senha", "Esqueci a senha da rede e preciso de uma nova."),
    ],
    "Impressora": [
        ("Impressora não imprime", "A fila de impressão fica parada e nada sai."),
        ("Papel atolando na impressora", "Atolamento frequente na bandeja principal."),
    ],
    "Lentidão no computador": [
        ("Computador muito lento", "O equipamento demora para abrir programas simples."),
        ("Travamentos frequentes", "O computador congela várias vezes ao dia."),
    ],
    "VPN / rede": [
        ("VPN não conecta", "Erro ao conectar na VPN em trabalho remoto."),
        ("Sem acesso à internet", "O ponto de rede da minha mesa está sem conexão."),
    ],
    "E-mail": [
        ("Caixa de e-mail cheia", "Não consigo enviar nem receber mensagens."),
        ("E-mail não sincroniza no celular", "A conta parou de atualizar no smartphone."),
    ],
    "Instalação de software": [
        ("Instalar software de planilhas", "Preciso de um programa para análise de dados."),
        ("Atualização de programa", "Aviso de versão desatualizada ao abrir o sistema."),
    ],
    "Equipamento (hardware)": [
        ("Monitor sem imagem", "O monitor liga, mas não exibe nada."),
        ("Teclado com teclas falhando", "Algumas teclas não respondem."),
    ],
    "Sistema ERP": [
        ("Erro ao emitir relatório no ERP", "Mensagem de erro ao gerar o relatório mensal."),
        ("Permissão de acesso no ERP", "Preciso de acesso a um módulo do sistema."),
    ],
}
PESOS_CATEGORIAS = [22, 18, 14, 12, 10, 10, 8, 6]

PRAZO_HORAS = {
    Prioridade.CRITICA: 4,
    Prioridade.ALTA: 24,
    Prioridade.MEDIA: 72,
    Prioridade.BAIXA: 120,
}


def _sortear_status(rng: random.Random, idade_dias: int) -> Status:
    if idade_dias > 14:
        pesos = [2, 4, 4, 90]
    elif idade_dias > 3:
        pesos = [10, 20, 15, 55]
    else:
        pesos = [35, 30, 15, 20]
    ordem = [Status.ABERTO, Status.EM_ANDAMENTO, Status.PENDENTE, Status.CONCLUIDO]
    return rng.choices(ordem, weights=pesos)[0]


def gerar_chamados(qtd: int = 150, semente: int = 42, agora: datetime | None = None) -> list[Chamado]:
    """Gera ``qtd`` chamados dos últimos ~180 dias. Mesma semente = mesmos dados."""
    rng = random.Random(semente)
    agora = (agora or datetime.now()).replace(microsecond=0)
    prioridades = list(Prioridade)
    urgencias = list(Urgencia)
    categorias = list(CATEGORIAS)
    chamados: list[Chamado] = []

    for indice in range(qtd):
        idade_dias = rng.randint(0, 180)
        abertura = agora - timedelta(
            days=idade_dias, hours=rng.randint(0, 23), minutes=rng.randint(0, 59)
        )
        categoria = rng.choices(categorias, weights=PESOS_CATEGORIAS)[0]
        titulo, descricao = rng.choice(CATEGORIAS[categoria])
        prioridade = rng.choices(prioridades, weights=[30, 40, 22, 8])[0]
        urgencia = rng.choices(urgencias, weights=[25, 45, 30])[0]
        prazo = abertura + timedelta(hours=PRAZO_HORAS[prioridade])
        status = _sortear_status(rng, idade_dias)

        if status == Status.ABERTO and rng.random() < 0.6:
            responsavel = None
        else:
            responsavel = rng.choice(RESPONSAVEIS)

        conclusao = None
        if status == Status.CONCLUIDO:
            horas = PRAZO_HORAS[prioridade] * rng.uniform(0.3, 1.6)
            conclusao = min(abertura + timedelta(hours=horas), agora)

        chamados.append(
            Chamado(
                numero=1001 + indice,
                titulo=titulo,
                descricao=descricao,
                solicitante=rng.choice(SOLICITANTES),
                setor=rng.choices(SETORES, weights=PESOS_SETORES)[0],
                categoria=categoria,
                responsavel=responsavel,
                data_abertura=abertura,
                data_conclusao=conclusao,
                status=status,
                prioridade=prioridade,
                urgencia=urgencia,
                prazo=prazo,
            )
        )
    return chamados
