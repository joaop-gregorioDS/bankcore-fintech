# Baseline P5 — Observability Architecture & Signals Audit

**Data da auditoria:** 2026-09-20
**Commit de referência:** `ad7c73e`
**Tag local:** `bankcore-p4-redis-resilience`
**Branch de trabalho:** `p5/observability`
**Escopo:** somente leitura; nenhum runtime, Compose, dependência ou workflow foi alterado nesta auditoria.

## 1. Resumo executivo

O BankCore já possui alguns sinais úteis, mas eles não formam ainda uma trilha operacional contínua para uma operação financeira.

- O Risk Service grava logs em JSON e registra falhas de autenticação sem incluir o token.
- Auth possui apenas um warning explícito para a entrada em fallback local do rate limit.
- O Audit Consumer e o Outbox Publisher têm mecanismos de segurança para sanitizar erros, mas não possuem uma superfície de logs estruturados operacionalmente completa.
- O evento `transaction.completed.v1` contém `correlation_id`, e atualmente ele é o próprio `transaction_id`.
- Não há middleware explícito de `request_id`, `traceparent` ou propagação de contexto W3C.
- A chamada Transactions → Risk envia identificadores no corpo, mas não propaga contexto de trace por HTTP.
- O Publisher envia o evento para Kafka sem headers de trace/correlação; o Audit Consumer recupera a correlação apenas do payload.
- Não foram encontradas métricas Prometheus, instrumentação OpenTelemetry, dashboards Grafana ou alertas versionados.
- Health/readiness cobrem principalmente HTTP e PostgreSQL. Publisher, Audit Consumer, Kafka e a dependência Redis não possuem uma superfície uniforme de readiness de aplicação.

Conclusão: a correlação de negócio sobrevive no evento, mas a correlação operacional perde-se entre as fronteiras HTTP e Kafka. O P5 deve primeiro criar uma identidade técnica de requisição/trace, mantendo-a distinta da identidade financeira da operação.

## 2. Matriz por componente

| Componente | Logs atuais | Métricas | Tracing/correlation | Health/readiness | Estado P5-A |
|---|---|---|---|---|---|
| Auth | Logs padrão do runtime; warning explícito no fallback local do Redis | Ausentes | Sem `request_id`, `traceparent` ou middleware; `jti` não é correlação | `/auth/health` e `/auth/readiness`; readiness verifica PostgreSQL | Parcial |
| Nginx | Access/error logs padrão; sem `log_format` customizado | Ausentes | Encaminha `X-Real-IP`/`X-Forwarded-For`, mas não gera/propaga `X-Request-ID` ou `traceparent` | `/health` público aponta para Transactions; não há agregação de readiness | Parcial |
| Transactions | Logs padrão do Uvicorn/runtime; sem logger operacional próprio | Ausentes | `transaction_id` e `correlation_id` existem no domínio/evento; não há propagação HTTP | `/health` e `/readiness`; readiness verifica PostgreSQL | Parcial |
| Risk | `AddJsonConsole`; warning de autenticação registra somente o tipo da falha | Ausentes | Não há `Activity`/OTel nem emissão explícita de trace/correlation; `transaction_id` chega no request JSON | `/health` e `/readiness`; readiness verifica tabela PostgreSQL | Parcial |
| PostgreSQL | Healthcheck `pg_isready` no Compose | Sem exporter ou métricas coletadas pelo projeto | Não aplicável diretamente | Healthcheck de processo/conexão | Básico |
| Redis | Healthcheck `PING`; warning de fallback no Auth | Sem métricas coletadas pelo projeto | Sem correlação de tentativa de login | Estado operacional observado apenas pelo Auth/fallback | Básico |
| Outbox Publisher | Erros sanitizados persistidos em `last_error`; sem logs de ciclo de claim/publish | Ausentes | Evento contém `correlation_id`, mas não há trace headers Kafka | Sem health/readiness próprio | Parcial |
| Kafka | Broker possui healthcheck nos ambientes descartáveis | Sem métricas do broker expostas ao projeto | Evento carrega correlação no payload; publisher não envia trace headers | Healthcheck técnico nos Compose de teste | Básico |
| Audit Consumer | Logger criado e `basicConfig` no entrypoint; não há emissão operacional consistente | Ausentes | Persiste `correlation_id` no payload do evento; não propaga trace | Sem endpoint de health/readiness | Parcial |

## 3. Evidências relevantes

### 3.1 Identidade de negócio existente

`services/transactions-service/app/events.py` define o envelope `transaction.completed.v1` com:

- `event_id` determinístico por transação, tipo e versão;
- `correlation_id` igual ao `transaction.id`;
- `data.transaction_id`, contas, valor em centavos e dados de Risk.

`services/audit-service/audit_app/contracts.py` valida e preserva essa correlação. O Audit Consumer grava o payload e aplica deduplicação por `event_id`.

Isso é uma boa identidade de negócio para auditoria, mas não substitui um trace técnico. Uma mesma operação pode atravessar várias requisições, retries e redeliveries; esses eventos precisam compartilhar contexto técnico sem transformar IDs financeiros em labels de métricas.

### 3.2 HTTP e gateway

`infra/nginx/bankcore.conf` encaminha `Host`, `X-Real-IP`, `X-Forwarded-For` e `Authorization`. Não há configuração explícita para:

- gerar ou aceitar `X-Request-ID`;
- propagar `traceparent`/`tracestate`;
- definir formato JSON de access log;
- mascarar ou excluir explicitamente dados sensíveis de logs customizados.

As APIs não possuem middleware próprio de request logging ou exception handling estruturado. Os endpoints de health/readiness retornam estado técnico, mas não um identificador de diagnóstico.

### 3.3 Transactions → Risk

`services/transactions-service/app/risk_client.py` implementa retry seletivo, refresh de token e circuit breaker. A chamada inclui identificadores financeiros no JSON e o token interno no header `Authorization`, mas não inclui `traceparent`, `X-Request-ID` ou um correlation header técnico.

O comportamento de resiliência é forte, porém seus retries, abertura do circuito, latência e resultado não são observáveis por métricas ou logs estruturados.

### 3.4 Outbox → Kafka → Audit

O Publisher:

- reclama eventos com `FOR UPDATE SKIP LOCKED` e lease PostgreSQL;
- publica com `acks=all` e idempotência do producer;
- sanitiza erros antes de persistir `last_error`;
- não registra explicitamente `event_id`, `correlation_id`, tentativa, latência ou resultado em logs.

O Audit Consumer:

- valida contrato e chave Kafka;
- grava antes de commitar o offset;
- deduplica por `event_id`;
- envia falhas para retry/DLQ com headers operacionais sanitizados.

Os headers de retry preservam tópico/partição/offset e razão sanitizada, mas não há `traceparent` nem um campo técnico equivalente. Após uma redelivery, a investigação depende do `event_id`/`correlation_id` do payload e dos metadados Kafka.

## 4. Onde a correlação se perde

```text
Cliente
  │  sem request_id/trace context padronizado
  ▼
Nginx
  │  sem geração/propagação explícita de trace context
  ▼
Auth
  │  autentica, mas não emite contexto operacional
  ▼
Transactions
  │  chama Risk sem trace headers
  ▼
Risk
  │  JSON console, porém sem trace/correlation fields garantidos
  ▼
Ledger + Outbox
  │  correlation_id existe no evento, não nos logs
  ▼
Kafka
  │  publisher não copia trace context para headers
  ▼
Audit Consumer
     correlation_id recuperável do payload; trace técnico não
```

O ponto mais forte atual é a correlação de domínio no evento. O maior gap é a ausência de uma identidade técnica que sobreviva a HTTP, retries, publicação assíncrona e redelivery.

## 5. Riscos de dados sensíveis e cardinalidade

### 5.1 Dados que não podem entrar em logs, traces ou métricas

Nenhum sinal novo deve incluir integralmente:

- JWT, `Authorization` ou qualquer token interno;
- CPF/CNPJ, chave Pix, senha, hash de senha ou segredo;
- connection strings, chaves privadas, `AUTH_SERVICE_TOKEN` ou `RATE_LIMIT_KEY_SECRET`;
- payload financeiro completo quando o diagnóstico puder usar apenas IDs internos e resultado;
- dados pessoais retornados por DTOs de usuário.

Os sanitizadores existentes de Publisher e Audit são uma proteção parcial para mensagens de erro. Eles não substituem uma política central de redação para logs HTTP, runtime e futuro tracing.

### 5.2 Labels de baixa cardinalidade

Métricas futuras podem usar somente dimensões controladas, por exemplo:

- `service`;
- `environment`;
- `route_template`;
- `method`;
- `status_class`;
- `operation_type`;
- `decision`;
- `outcome`;
- `dependency`;
- `consumer_group`;
- `topic`;
- `retry_class`.

Não usar `transaction_id`, `event_id`, `user_id`, CPF/CNPJ, Pix key, `jti` ou `trace_id` como labels Prometheus. Esses valores podem existir em logs/traces controlados, com redaction e retenção definida.

## 6. Arquitetura proposta para P5

### 6.1 Identidades distintas

O P5 deve manter três conceitos separados:

| Identidade | Propósito | Exemplo de uso |
|---|---|---|
| `request_id` | Diagnóstico de uma entrada HTTP | resposta/log da requisição |
| `trace_id`/`span_id` | Trace técnico distribuído | spans HTTP, PostgreSQL, Kafka e retries |
| `correlation_id` | Identidade de negócio da operação | `transaction.completed.v1`, audit e reconciliação |

Para o fluxo financeiro, `correlation_id` pode continuar sendo o identificador da transação. O trace técnico deve ser propagado independentemente e não deve alterar a semântica do ledger.

### 6.2 Propagação

1. Nginx preserva `traceparent`/`tracestate` válidos e encaminha `X-Request-ID` controlado.
2. Cada serviço Python cria ou aceita um request context validado e inclui `request_id`, `trace_id` e `span_id` nos logs.
3. Transactions propaga contexto W3C na chamada HTTP para Risk.
4. O Publisher injeta contexto W3C em headers Kafka quando houver contexto disponível.
5. O Audit Consumer extrai headers Kafka e cria um novo span de consumo ligado ao trace de produção.
6. O envelope financeiro continua versionado e mantém `correlation_id` como campo de negócio.

### 6.3 Componentes recomendados

Arquitetura mínima, a validar na implementação:

```text
Auth / Transactions / Risk / Publisher / Audit Consumer
        │ logs estruturados + OTLP traces + métricas
        ▼
OpenTelemetry Collector
        ├── Prometheus (métricas)
        ├── Tempo ou backend compatível (traces)
        └── stdout estruturado inicialmente; backend de logs em fase própria
                    │
                    ▼
                 Grafana
```

O Collector deve permanecer fora do caminho financeiro: se observabilidade falhar, a transação, o ledger, o outbox e o consumo idempotente continuam seguindo suas políticas atuais.

## 7. Sinais prioritários

### Logs

Campos mínimos: `timestamp`, `level`, `service`, `environment`, `request_id`, `trace_id`, `span_id`, `correlation_id` quando aplicável, `operation`, `outcome`, `duration_ms` e `error.type`.

### Traces

Spans prioritários:

- entrada no Nginx/API;
- autenticação e autorização sem atributos de token;
- chamada Transactions → Risk;
- transação PostgreSQL/ledger;
- criação e claim do outbox;
- publish Kafka;
- consume/retry/DLQ;
- persistência Audit PostgreSQL.

### Métricas

Primeiro conjunto recomendado:

- requisições por serviço, rota e classe de status;
- latência por rota e dependência;
- decisões Risk por `decision`/`outcome`;
- circuit breaker do Risk por estado;
- retries e falhas de chamada Risk;
- outbox pendente, idade máxima, tentativas e falhas;
- mensagens consumidas, redeliveries, retries e DLQ;
- lag Kafka por consumer group;
- readiness e modo degradado do rate limit;
- conexões/falhas de PostgreSQL e Redis em nível agregado.

## 8. Gaps priorizados

| Prioridade | Gap | Evidência | Próxima fase |
|---|---|---|---|
| P0/P1 operacional | Tokens, IDs pessoais ou payloads podem ser expostos por logs de infraestrutura se configurações padrão mudarem | Nginx/runtime sem política central de redaction | P5-B |
| P1 | Não existe request ID técnico comum | Ausência de middleware/header dedicado | P5-B |
| P1 | Trace context não atravessa HTTP/Kafka | Ausência de `traceparent`/OTel e headers Kafka | P5-C |
| P1 | Falhas e retries não têm métricas | Nenhum exporter/instrumentation encontrado | P5-D |
| P1 | Publisher/Audit não têm health/readiness operacional | Apenas processos/Compose de teste | P5-F |
| P1 | Nginx expõe apenas health de Transactions | `location /health` único | P5-F |
| P2 | Não há backend de logs pesquisável | Logs ficam dependentes do runtime/container | P5-E/F |
| P2 | Retenção e sampling ainda não definidos | Nenhuma política versionada | P5-A decisão / P5-C |

## 9. Backlog aprovado para detalhamento

- **P5-B:** contexto de request, correlation e redaction; logs estruturados Python/.NET/Nginx.
- **P5-C:** OpenTelemetry SDKs, propagação HTTP/Kafka e Collector descartável.
- **P5-D:** métricas de baixa cardinalidade para HTTP, Risk, outbox, Kafka, Redis e PostgreSQL.
- **P5-E:** dashboards Grafana para fluxo financeiro, dependências e DLQ.
- **P5-F:** alertas, readiness operacional e visibilidade de falhas sem bloquear o caminho financeiro.
- **P5-G:** E2E que prova `request → Auth → Transactions → Risk → Ledger → outbox → Kafka → Audit` com um identificador técnico pesquisável.
- **P5-H:** runners locais e GitHub Actions para Collector, métricas, traces, redaction e E2E.

## 10. Decisões de segurança para todas as fases P5

- Observabilidade é best-effort e nunca fonte da verdade financeira.
- Falha do Collector, Prometheus, Grafana ou backend de traces não pode impedir ledger, outbox ou Audit Consumer.
- Nenhum segredo ou identificador pessoal será usado como label de métrica.
- Traces não carregarão `Authorization`, JWT, senha, chave Pix ou CPF/CNPJ.
- Logs de erro continuarão limitados, sanitizados e sem payloads completos por padrão.
- IDs de negócio só aparecerão onde forem necessários para investigação e estarão sujeitos à retenção e acesso apropriados.

## 11. Status da baseline

**P5-A concluído localmente.** O repositório está pronto para discutir o contrato de logging/correlation de P5-B. Nenhuma dependência de observabilidade foi adicionada e nenhum serviço foi iniciado ou acessado durante a auditoria.
