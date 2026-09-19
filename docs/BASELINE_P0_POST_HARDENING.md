# BankCore 2.0 — Baseline P0 pós-hardening

Data da baseline: 2026-09-19  
Commit de referência: `840eba4` — Merge P0-F data and privacy hardening  
Tag local: `bankcore-p0-hardening`

Esta baseline registra o estado local após as fases críticas de hardening. Ela não representa produção pronta: a VPS não foi acessada, não houve push e TLS externo, CI/CD, migrações versionadas, observabilidade e backups continuam pendentes.

## Matriz P0

| Área | Baseline original | Estado pós-hardening | Classificação |
| --- | --- | --- | --- |
| Demo/deposit | Seeds e depósito demo sem isolamento suficiente | `DEMO_MODE=false` por padrão; seeds e depósito condicionais | Eliminado localmente; deployment externo não verificado |
| Money | `float` na entrada/domínio | `Decimal` na borda e centavos inteiros no ledger | Eliminado no domínio; saída JSON preserva compatibilidade numérica |
| Idempotência | Chave global e ownership insuficiente | Escopo por usuário/conta/operação, fingerprint e constraint PostgreSQL | Eliminado; concorrência real validada |
| Containers | Root, `--reload` e exposição ampla | Aplicações non-root, sem reload de produção, imagens fixadas, healthchecks e rede interna | Eliminado localmente |
| JWT | HS256 compartilhado | RS256, `kid`, issuer/audience, claims obrigatórias e rotação | Eliminado |
| Service-to-service | Reuso do JWT do usuário | Token interno com audience/scope próprios | Eliminado |
| Diretório Pix | Endpoint legado e exposição excessiva | POST interno, lookup exato, DTO mínimo, prefixo bloqueado no gateway e clientes sem contrato legado | Eliminado/fortemente reduzido |
| Health | Health superficial | Health e readiness com verificação de banco | Melhorado |
| Portas | Serviços internos potencialmente publicados | Apenas Nginx publicado no Compose | Eliminado localmente; deployment externo não verificado |
| Secrets | Configuração baseada apenas em `.env` | `.env` fora do Git; chave privada montada somente no Auth; Transactions recebe chaves públicas | Mitigado; sem secret manager |
| Testes | Cobertura crítica limitada | Testes de demo, dinheiro, idempotência, JWT e privacidade; PostgreSQL real usado no P0-C | Melhorado; ainda sem execução automática em CI |
| CI/CD | Ausente | Ausente | Pendente |
| Migrations | `create_all()` e SQL manual misturados | Situação ainda existente | Pendente para P1-A |
| Observabilidade | Ausente | Ausente | Pendente |
| Backups | Sem estratégia automatizada | Sem estratégia automatizada | Pendente |

## Evidências locais

- `docker compose config` e build local passaram.
- Compose production-like iniciou com os cinco serviços saudáveis.
- Aplicações e Nginx foram verificados sem execução root; produção não usa `--reload`.
- Health/readiness responderam com sucesso e somente o gateway publicou porta no host.
- P0-C teve 22/22 testes PostgreSQL, 20 rodadas com 10 requisições concorrentes e nenhuma duplicação ou sobra `PROCESSING`.
- A matriz JWT Docker passou integralmente, incluindo claims, algoritmo, `kid`, rotação, audience/scope e fallback de rate limit.
- A validação P0-F confirmou endpoint legado removido, rota interna invisível no gateway, resposta mínima e ownership entre contas.
- A suíte local final teve 35 testes executados, 23 aprovados e 12 skips conhecidos por dependências criptográficas/PostgreSQL ausentes no host; os testes JWT críticos foram executados dentro da imagem Docker.

## Riscos residuais

1. A aplicação ainda executa `Base.metadata.create_all()` no startup e depende de `init.sql`/SQL manual para parte do ciclo de banco.
2. O segredo de bootstrap entre serviços ainda é uma configuração compartilhada; não há mTLS, Vault, KMS ou secret manager.
3. Não há workflow CI, auditoria automatizada de dependências, secret scan, SAST, SBOM ou scan de imagens.
4. Não há OpenTelemetry, métricas, tracing, dashboards nem política formal de retenção/redação de logs.
5. Não há backup/restore automatizado e validado para PostgreSQL.
6. TLS externo, firewall, configuração e estado da VPS permanecem não verificados por decisão de escopo.
7. A configuração comum ainda lista origens locais de desenvolvimento; a separação completa entre configuração de desenvolvimento e produção permanece uma melhoria futura.

## Próxima fase

P1 começa por `p1/database-migrations`, sem introduzir .NET, Kafka, observabilidade ou IaC. O primeiro objetivo é substituir a criação automática de schema por um ciclo Alembic reproduzível, preservando bancos existentes e permitindo inicialização limpa por `upgrade head`.
