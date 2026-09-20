# P5-C — OpenTelemetry Distributed Tracing

## Objetivo

O BankCore usa W3C Trace Context para acompanhar uma operação entre HTTP, Risk,
ledger, outbox, Kafka e Audit Consumer. O tracing é diagnóstico: o PostgreSQL é
a fonte da verdade financeira e o Kafka continua sendo propagação posterior ao
commit.

## Propagação

- FastAPI é instrumentado automaticamente para spans HTTP.
- Transactions injeta `traceparent` e `tracestate` na chamada HTTP para Risk.
- O publisher injeta os mesmos headers nos headers Kafka de
  `transaction.completed.v1`.
- O Audit Consumer extrai os headers Kafka e cria o span de consumo.
- `request_id`, `correlation_id`, `event_id` e `transaction_id` continuam sendo
  identificadores distintos; nenhum substitui o Trace Context.

Spans de domínio relevantes:

```text
risk.assess
ledger.commit
outbox.persist
kafka.produce transaction.completed.v1
kafka.consume transaction.completed.v1
audit.persist
```

## Collector e fail-open

O arquivo `docker-compose.p5-tracing.yml` adiciona um OpenTelemetry Collector
descartável, sem publicar portas no host. Os serviços exportam por OTLP gRPC
quando `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` está configurado. Sem endpoint, o
SDK permanece sem exporter; uma falha ou indisponibilidade do Collector não
bloqueia o caminho financeiro.

O Collector de teste usa um exporter de debug para tornar os spans verificáveis
sem depender de Jaeger, Tempo, Prometheus ou Grafana.

## Segurança

Somente atributos operacionais allowlisted são adicionados aos spans manuais.
Não registrar ou propagar como atributo de telemetria:

- tokens, `Authorization`, senhas, chaves privadas ou secrets;
- CPF/CNPJ, chave Pix, e-mail ou connection strings;
- payload financeiro completo;
- identificadores de alta cardinalidade como labels de métricas.

Os headers W3C carregam contexto de tracing, não credenciais. O token interno
continua sendo transportado e validado exclusivamente pelo contrato de
autenticação existente, sem ser copiado para spans ou logs.

## Validação local

O runner descartável `scripts/p5-tracing.py` (com wrappers PowerShell e Bash):

1. gera chaves JWT temporárias e secrets efêmeros;
2. valida e constrói o Compose base mais o overlay de tracing;
3. aplica as migrations em bancos descartáveis;
4. executa o fluxo E2E Auth → Nginx → Transactions → Risk → Ledger → Outbox →
   Kafka → Audit;
5. confirma os spans obrigatórios no output do Collector;
6. verifica a ausência de valores sensíveis proibidos;
7. destrói containers, volumes e redes temporários mesmo em caso de falha.

O overlay não altera o Compose principal e não acessa infraestrutura externa.
