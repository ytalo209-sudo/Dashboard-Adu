# Diagnóstico para a integração com o sistema .NET (etapa 2)

Nenhum código de integração real deve ser escrito antes de responder isto. Hoje o projeto
NÃO assume banco, tabelas, endpoints nem credenciais: `integrations/dotnet_api_client.py`
só cuida do transporte (HTTPS, token, timeout) e `database/connection_factory.py` só monta
conexões a partir de variáveis de ambiente.

## 1. Tecnologia

- [ ] Qual banco de dados o sistema de chamados usa? (SQL Server, PostgreSQL, MySQL, Oracle, outro)
- [ ] O sistema é ASP.NET (Web API, MVC, Razor), .NET Framework ou .NET moderno?
- [ ] É um produto de mercado (ex.: com API própria) ou desenvolvimento interno?

## 2. API REST (caminho preferido: respeita as regras de negócio do sistema)

- [ ] Existe API REST? Há documentação (Swagger/OpenAPI)? Qual a URL base por ambiente?
- [ ] Endpoints de consulta: lista de chamados, detalhe, histórico.
- [ ] Endpoints de alteração: prioridade, urgência, responsável, status, observações.
- [ ] Autenticação: Bearer/JWT, API key, OAuth2, Windows/AD? Como obter e renovar o token?
- [ ] Autorização: a API aplica permissão por usuário ou por conta de serviço?
- [ ] Formato de datas, fuso horário, paginação e limites de requisição.

## 3. Acesso direto ao banco (alternativa, somente leitura)

- [ ] A TI/DBA autoriza uma conta exclusiva só com `SELECT`, em réplica ou banco de relatórios?
- [ ] Nomes das tabelas e colunas de chamados, status, prioridade, urgência, setor, responsável e histórico.
- [ ] Como o sistema representa "atrasado" e o prazo (SLA)? Há tabela de SLA?
- [ ] O banco exige TLS? Qual o driver ODBC/cliente instalado?
- [ ] Escritas diretas no banco devem ser evitadas: contornam regras, gatilhos e auditoria do sistema original.

## 4. Infraestrutura e segurança

- [ ] De onde o dashboard vai rodar (servidor interno, VM, contêiner)? Há rota de rede até a API/banco?
- [ ] Firewall, VPN, proxy ou allowlist de IP?
- [ ] Onde guardar segredos (variáveis de ambiente, Key Vault, Secret Manager)?
- [ ] Como autenticar quem usa o dashboard (SSO/AD/Entra ID) e mapear para os perfis Leitor/Analista/Gestor?
- [ ] Exigências de LGPD, retenção de logs e aprovação da área de segurança.

## 5. Quando você tiver as respostas

Basta implementar `ChamadoRepository` (`repositories/base.py`) em uma nova classe, por exemplo
`ApiChamadoRepository` ou `SqlChamadoRepository`, e escolher `DATA_SOURCE` no `.env`.
Serviços, regras, auditoria e interface continuam iguais.
