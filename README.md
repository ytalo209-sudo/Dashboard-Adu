# Dashboard de Gestão de Chamados de TI

Ferramenta complementar ao sistema de chamados da empresa. **Etapa 1 (esta): versão simulada**, com dados fictícios em memória e nenhuma conexão com banco de produção.

## Como executar

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # já vem com DATA_SOURCE=simulado
streamlit run app.py
```

Testes:

```bash
python -m pytest
```

Na barra lateral há três usuários fictícios (Gestora, Analista, Leitor) para testar as permissões.

## Arquitetura

```
app.py                    ponto de entrada (streamlit run app.py)
config/settings.py        variáveis de ambiente -> objetos validados (segredos em SecretStr)
domain/                   modelos Pydantic, filtros e exceções (sem banco, sem interface)
database/                 Connection Factory (SQLAlchemy): engine, pool, sessões, erros
integrations/             cliente HTTP genérico para a API .NET (sem endpoints inventados)
repositories/             contrato (base.py) + implementação simulada (mock_repository.py)
services/                 permissões, regras de negócio com auditoria, indicadores
dashboard/                interface Streamlit: filtros, cards, gráficos Plotly, tabela, ações
tests/                    unitários e de integração
docs/DIAGNOSTICO.md       o que levantar antes de integrar com o ambiente real
```

Fluxo: `dashboard` -> `services` -> `repositories` (interface) -> implementação (simulada hoje, API ou SQL somente leitura depois). Trocar a fonte de dados não exige mexer em serviços nem na interface.

## O que já funciona

- Cards: total, abertos, em andamento, pendentes, concluídos, críticos, atrasados e tempo médio.
- Gráficos: por setor, prioridade e status; evolução mensal (abertos x concluídos); tempo médio por mês; problemas recorrentes.
- Tabela interativa com todos os campos e filtros por período, setor, responsável, status, prioridade, atraso e busca.
- Ações: alterar prioridade, urgência, responsável e status; adicionar observação; ver histórico.
- Regras de negócio: perfil Leitor só consulta; Analista altera status e comenta; Gestor altera tudo. Prioridade Crítica, conclusão e reabertura exigem confirmação. Não conclui sem responsável; chamado concluído só muda se for reaberto.
- Auditoria: cada alteração registra usuário, data/hora, campo, valor anterior e novo (histórico + log `chamados.auditoria`).
- Exportação dos chamados filtrados em CSV.

## Definições dos indicadores

- **Atrasado**: não concluído e com prazo vencido.
- **Crítico**: prioridade Crítica ainda não concluída.
- **Tempo médio de atendimento**: média entre abertura e conclusão, só de chamados concluídos.

## Possíveis erros

| Sintoma | Causa e solução |
|---|---|
| `ModuleNotFoundError: streamlit` (ou plotly, sqlalchemy) | Dependências não instaladas: `pip install -r requirements.txt` |
| Tela mostra "DATA_SOURCE ... não implementado" | Só `simulado` existe nesta etapa. Ajuste o `.env` |
| `DatabaseConfigError: Variáveis de ambiente ausentes` | Faltam DB_HOST, DB_NAME, DB_USER ou DB_PASSWORD (a mensagem nunca mostra valores) |
| `DependencyMissingError` | Instale `sqlalchemy` e o driver do seu banco (pyodbc, psycopg2, pymysql) |
| `IntegrationError: ... HTTPS` | A URL da API precisa começar com `https://` |
| Alterações somem ao reiniciar | Esperado no modo simulado: os dados vivem em memória |

## Próximas etapas

1. Responder `docs/DIAGNOSTICO.md` (banco, API, autenticação, rede).
2. Criar `ApiChamadoRepository` ou `SqlChamadoRepository` (somente leitura primeiro), com mapeamento confirmado de tabelas ou endpoints.
3. Autenticação corporativa (SSO/AD) no lugar dos usuários simulados.
4. Gravação via API oficial do sistema, mantendo a confirmação e a auditoria.

## Segurança

Credenciais só em variáveis de ambiente (`.env` está no `.gitignore`); sessão de banco somente leitura por padrão; consultas parametrizadas via SQLAlchemy; TLS exigido por padrão (`DB_ENCRYPT=true`, API só HTTPS); mensagens de erro sem host, usuário ou senha. Para produção, use também um usuário de banco só com `SELECT`.
