# P2-A — Risk Service em ASP.NET Core/C#

Este documento transforma a ADR-001 em um contrato inicial e em critérios verificáveis para a primeira implementação do Risk Service. O P2-A é deliberadamente documental: não adiciona código C#, não altera o Compose e não muda o fluxo financeiro atual.

## Objetivo

Adicionar ao BankCore um serviço interno de avaliação de risco determinística, em ASP.NET Core/C#, preservando estas regras:

- Transactions continua sendo a única autoridade para contas, idempotência financeira, saldos e ledger;
- Auth continua sendo a autoridade para identidade, JWT e resolução interna Pix;
- Risk possui somente suas avaliações e regras;
- nenhum cliente externo acessa o Risk diretamente;
- nenhuma decisão de risco grava efeito financeiro por conta própria.

## Contrato inicial

### Endpoint

```text
POST /internal/risk/assessments
```

O endpoint é interno, exige JWT de serviço e não deve ser roteado pelo Nginx público.

### Request

| Campo | Tipo | Regra |
| --- | --- | --- |
| `transaction_id` | UUID | obrigatório; identidade da operação financeira |
| `source_account_id` | UUID | obrigatório |
| `destination_account_id` | UUID | obrigatório |
| `amount_cents` | inteiro | positivo; sem `float`/`Decimal` no contrato |
| `operation_type` | enum | inicialmente somente `PIX` |

Exemplo:

```json
{
  "transaction_id": "11111111-1111-1111-1111-111111111111",
  "source_account_id": "22222222-2222-2222-2222-222222222222",
  "destination_account_id": "33333333-3333-3333-3333-333333333333",
  "amount_cents": 1010,
  "operation_type": "PIX"
}
```

No P2-D, `assessment_id` ainda era efêmero. No P2-E ele passa a ser o UUID persistido da avaliação; replay do mesmo `transaction_id` e fingerprint devolve o mesmo identificador.

### Response

```json
{
  "assessment_id": "44444444-4444-4444-4444-444444444444",
  "transaction_id": "11111111-1111-1111-1111-111111111111",
  "decision": "APPROVED",
  "risk_score": 12,
  "reasons": ["amount_within_limit"],
  "rules_version": "v1"
}
```

Decisões:

- `APPROVED`: Transactions pode prosseguir para a transação financeira;
- `REVIEW`: Transactions não lança no ledger automaticamente;
- `REJECTED`: Transactions não lança no ledger.

### Erros

| HTTP | Situação | Regra para Transactions |
| --- | --- | --- |
| `400` | JSON/headers inválidos | corrigir contrato; não repetir cegamente |
| `401` | JWT ausente, inválido ou expirado | falha de autenticação serviço-a-serviço |
| `403` | audience/scope/sub não permitidos | rejeitar; não usar JWT de usuário |
| `409` | mesmo `transaction_id` com payload divergente | tratar como conflito de identidade |
| `422` | valor, UUID ou operação inválidos | não chamar o ledger |
| `503` | Risk indisponível ou banco não pronto | fail-closed |
| `504` | deadline excedido | fail-closed; retry somente se seguro |

Respostas de erro não devem conter dados de usuários, chaves Pix, tokens, SQL, stack traces ou identificadores internos desnecessários.

## Segurança interna

O contrato esperado do token é:

```text
iss   = bankcore-auth
aud   = bankcore-internal
scope = risk:assess
sub   = service:transactions
```

O Risk deverá fixar `RS256`, validar `kid`, issuer, audience, scope, subject e claims temporais. A chave privada nunca será copiada para a imagem ou para o ambiente do Risk.

O atual mecanismo de Auth emite/aceita o escopo específico de Transactions para o diretório Pix. A extensão para `risk:assess` será uma mudança explícita do contrato de autenticação em uma etapa posterior; não deve ser improvisada dentro do endpoint de avaliação.

## Modelo e ownership

O banco dedicado será `bankcore_risk`, com migration history separado. O modelo inicial de `risk_assessments` deverá preservar:

```text
id                         UUID primary key
transaction_id             UUID
source_account_id          UUID
destination_account_id     UUID
amount_cents               BIGINT
operation_type             VARCHAR/enum
decision                   VARCHAR/enum
risk_score                 INTEGER
reasons                    JSONB
rules_version              VARCHAR
request_fingerprint        CHAR(64)
created_at                 timestamp with timezone
```

Constraints mínimas:

```text
PRIMARY KEY (id)
UNIQUE (transaction_id)
```

O `request_fingerprint` é SHA-256 da forma canônica normalizada de `transaction_id`, contas, `amount_cents` e `operation_type`. A primeira avaliação é inserida com a decisão e seus reasons na mesma operação de persistência. Uma corrida que viola a constraint única é relida deliberadamente: fingerprint igual é replay; fingerprint diferente retorna `409 Conflict`.

O banco `bankcore_risk` possui histórico Alembic/EF Core próprio e não é migrado automaticamente pelo processo da API. Antes de iniciar o Risk, a migration one-shot deve ser executada explicitamente:

```text
docker compose build risk-service
docker compose --profile migration run --rm migrate-risk
docker compose up -d --wait risk-service
```

O `/health` permanece liveness independente. O `/readiness` só responde pronto quando consegue consultar a tabela `risk_assessments`; banco ausente, schema ausente ou conexão indisponível resultam em `503`.

Para validação descartável da persistência, use `docker-compose.risk-test.yml`: ele mantém um PostgreSQL exclusivo de teste, executa o migrador, roda os quatro testes de integração (migration, replay após novo serviço, conflito e 20 requisições concorrentes) e deve ser destruído com `down --volumes`:

```text
docker compose -f docker-compose.risk-test.yml up -d postgres-risk-test
docker compose -f docker-compose.risk-test.yml run --build --rm migrate-risk-test
docker compose -f docker-compose.risk-test.yml run --build --no-deps --rm risk-integration-tests
docker compose -f docker-compose.risk-test.yml down --volumes --remove-orphans
```

O UUID das contas é uma referência lógica ao domínio de Transactions, não uma foreign key entre bancos. A consistência dessa referência será verificada pelo contrato de chamada, sem permitir acesso cruzado ao schema.

## Sequência de integração

```text
Cliente → Transactions
              │ autentica/valida ownership/idempotência
              ▼
        Risk /internal/risk/assessments
              │ decisão persistida no bankcore_risk
              ▼
        Transactions
              │ somente APPROVED
              ▼
        Ledger no banco bankcore_transactions
```

Regras de sequência:

1. o cliente nunca chama Risk;
2. Transactions monta o request a partir de dados já validados;
3. a chamada ao Risk ocorre sem locks de conta e sem transação SQL longa aberta;
4. `APPROVED` é necessário para o caminho financeiro;
5. `REVIEW`, `REJECTED`, timeout e erro de infraestrutura não lançam no ledger;
6. o Risk não reexecuta nem confirma a operação financeira;
7. a estratégia final para crash entre a claim de idempotência e a avaliação será definida antes do P2-F.

## Regras determinísticas iniciais — `risk-rules-v1`

O P2-C implementa somente regras sintéticas e didáticas, baseadas nos dados que o contrato já fornece. Elas não representam um modelo real de fraude bancária.

| Regra | Condição | Pontos | Reason |
| --- | --- | ---: | --- |
| `AmountRiskRule` | `amount_cents <= 100000` | 0 | — |
| `AmountRiskRule` | `100000 < amount_cents <= 1000000` | 40 | `HIGH_AMOUNT` |
| `AmountRiskRule` | `amount_cents > 1000000` | 70 | `VERY_HIGH_AMOUNT` |
| `OperationTypeRule` | `operation_type = PIX` | 0 | — |
| `OperationTypeRule` | operação diferente de `PIX` | 40 | `UNSUPPORTED_OPERATION` |

O score composto é limitado a `0..100` e produz:

- `0..39` → `APPROVED`;
- `40..69` → `REVIEW`;
- `70..100` → `REJECTED`.

A ordem de execução das regras não altera score, decisão ou ordenação final dos reasons. A versão `risk-rules-v1` é obrigatória em toda avaliação.

O domínio ainda não implementa velocity, histórico do cliente, destinatário novo, comportamento anômalo ou ML, porque essas informações não existem no contrato/runtime atual.

## Critérios de aceite do P2-A

- [ ] Branch `p2/risk-service-dotnet` parte da `main` sincronizada em `389d49d`.
- [ ] ADR-001 está revisada e aprovada.
- [ ] Request e response possuem exemplos e tipos definidos.
- [ ] `APPROVED`, `REVIEW` e `REJECTED` têm semântica explícita.
- [ ] Erros de autenticação, validação, conflito, timeout e indisponibilidade têm contrato.
- [ ] Transactions, Auth e Risk têm ownership de dados documentado.
- [ ] `bankcore_risk` e seu histórico de migrations estão definidos sem acesso cruzado.
- [ ] O token interno exige `iss`, `aud`, `scope` e `sub` específicos.
- [ ] O cliente público, Nginx e JWT de usuário não acessam o endpoint interno.
- [ ] O Risk não grava no ledger e não aprova em caso de timeout/erro.
- [ ] A sequência evita manter locks/transações SQL abertos durante HTTP.
- [ ] Estrutura da solução .NET e responsabilidades de cada projeto estão definidas.
- [ ] Não há código C#, alteração de Compose/CI, Kafka, ML, deploy ou acesso à VPS nesta fase.

## Próximas fases propostas

| Fase | Escopo |
| --- | --- |
| P2-B | solução .NET, projetos, build e testes unitários mínimos |
| P2-C | domínio determinístico e regras sintéticas |
| P2-D | API interna segura, DTO estrito e autenticação `risk:assess` |
| P2-E | EF Core, PostgreSQL `bankcore_risk`, migrations próprias e persistência idempotente ✅ |
| P2-F | cliente Risk em Transactions, timeout, idempotência e fail-closed |
| P2-G | resiliência, testes de integração e CI |

Kafka, observabilidade avançada, IaC e ML permanecem fora destas fases iniciais.
