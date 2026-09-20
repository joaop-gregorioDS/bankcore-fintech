# ADR-001 — Contrato e fronteiras do Risk Service

- **Status:** proposto — P2-A
- **Data:** 2026-09-19
- **Escopo:** arquitetura e contrato; sem implementação nesta fase

## Contexto

O BankCore possui hoje dois serviços Python/FastAPI:

- **Auth:** identidade, credenciais, JWT e resolução interna de destinatários Pix;
- **Transactions:** contas, saldos, idempotência, transações Pix e ledger de partidas dobradas.

O fluxo financeiro atual chega ao ledger diretamente depois das validações de autenticação, ownership, destinatário e idempotência. O P2 introduzirá um serviço de risco determinístico em ASP.NET Core/C#, mas não deve deslocar a autoridade financeira para uma nova tecnologia.

O serviço novo precisa ser demonstrável em C#/.NET, possuir contrato verificável e integrar-se de forma segura sem expor uma API pública, sem consultar bancos de outros serviços e sem escrever diretamente no ledger.

## Decisão

Criar posteriormente um **Risk Service interno**, implementado em ASP.NET Core/C#, com estas fronteiras:

| Responsabilidade | Serviço proprietário |
| --- | --- |
| Usuário, credenciais e emissão de JWT | Auth |
| Resolução interna de chave Pix | Auth |
| Contas, saldos, idempotência e ledger | Transactions |
| Avaliação e histórico de risco | Risk |

O Risk Service terá um banco PostgreSQL dedicado chamado `bankcore_risk`. Somente o Risk Service poderá ler ou gravar suas tabelas. Não haverá acesso direto do Risk ao banco de Transactions nem acesso de Transactions às tabelas do Risk.

O primeiro contrato será síncrono e interno:

```http
POST /internal/risk/assessments
Authorization: Bearer <internal-service-jwt>
Content-Type: application/json
```

O endpoint não será publicado pelo Nginx, não será acessível por JWT de usuário e não terá equivalente público.

### Request canônico

```json
{
  "transaction_id": "uuid",
  "source_account_id": "uuid",
  "destination_account_id": "uuid",
  "amount_cents": 1010,
  "operation_type": "PIX"
}
```

Regras do request:

- `amount_cents` é inteiro positivo; valores monetários não atravessam o contrato como `float` ou `Decimal`;
- `operation_type` começa restrito a `PIX`;
- UUIDs e o valor são normalizados antes do fingerprint;
- `transaction_id` identifica a operação financeira que está sendo avaliada;
- nenhum `user_id`, JWT de usuário, password, chave Pix, documento ou dado desnecessário é enviado ao Risk.

### Response canônica

```json
{
  "assessment_id": "uuid",
  "transaction_id": "uuid",
  "decision": "APPROVED",
  "risk_score": 12,
  "reasons": ["amount_within_limit"],
  "rules_version": "v1"
}
```

`decision` aceita somente `APPROVED`, `REVIEW` ou `REJECTED`. `risk_score` é um inteiro com escala documentada pelo serviço. `reasons` contém códigos estáveis, não texto livre com dados pessoais.

### Idempotência da avaliação

Uma avaliação é imutável para determinado `transaction_id` e versão de regras. O Risk deverá:

1. retornar a avaliação existente quando o request normalizado for equivalente;
2. responder `409 Conflict` quando o mesmo `transaction_id` for reapresentado com campos relevantes diferentes;
3. persistir um fingerprint SHA-256 do request canônico;
4. impor uma constraint única para a identidade da avaliação, no mínimo `(transaction_id, rules_version)`.

Essa idempotência é independente da idempotência financeira de Transactions. O Risk não cria, confirma, estorna ou duplica lançamentos.

### Autenticação serviço-a-serviço

O contrato interno exigirá um JWT de serviço com:

```text
iss   = bankcore-auth
aud   = bankcore-internal
scope = risk:assess
sub   = service:transactions
```

O Risk validará explicitamente assinatura RS256, `kid`, issuer, audience, claims temporais obrigatórias, `jti` e o scope permitido. JWT de usuário será rejeitado mesmo que tenha assinatura válida. A private key ficará exclusivamente no Auth; o Risk receberá apenas as chaves públicas necessárias para verificação.

O endpoint de emissão/bootstrap de tokens deverá ser estendido de forma explícita para o chamador Transactions e seu scope de risco. Não será criado um segredo compartilhado novo como substituto do JWT, nem será permitido aceitar qualquer token RS256 válido sem audience/scope.

### Fluxo Transactions → Risk → Ledger

Na integração futura, Transactions deverá:

1. autenticar o usuário e validar ownership da conta de origem;
2. validar a chave de idempotência e normalizar o request monetário;
3. resolver e validar a conta de destino;
4. solicitar a avaliação ao Risk usando o JWT interno;
5. gravar no ledger somente quando a decisão for `APPROVED`;
6. não gravar no ledger para `REVIEW` ou `REJECTED`;
7. preservar a mesma resposta idempotente da operação financeira em replays.

O Risk nunca chama o ledger. A chamada HTTP não deverá ocorrer enquanto Transactions mantém locks de conta ou uma transação SQL aberta. A implementação deverá resolver a interação entre a claim de idempotência e a chamada externa sem deixar registros `PROCESSING` órfãos em caso de timeout ou crash.

### Timeout, indisponibilidade e fail-closed

O primeiro contrato será síncrono, com timeout curto e explícito, deadline propagado e tratamento distinto para:

- `400`/`422`: request inválido — não repetir automaticamente;
- `401`/`403`: credencial interna inválida — falha de integração/configuração;
- `409`: identidade da avaliação reutilizada com payload divergente;
- `503`/timeout: Risk indisponível — operação financeira não é aprovada;
- `REVIEW`/`REJECTED`: resposta de domínio — não há lançamento no ledger.

Para operações que exigem avaliação, indisponibilidade do Risk será **fail-closed**: Transactions não poderá transformar timeout, erro 5xx ou resposta desconhecida em `APPROVED`. Retry limitado, se adotado, deverá ser seguro e respeitar o mesmo `transaction_id`; não haverá fallback silencioso para aprovação.

### Persistência do Risk

O modelo inicial deverá conter, no mínimo:

```text
risk_assessments
  id
  transaction_id
  source_account_id
  destination_account_id
  amount_cents
  operation_type
  decision
  risk_score
  reasons              JSONB
  rules_version
  request_fingerprint
  created_at
```

O banco `bankcore_risk` terá um histórico de migrations próprio, compatível com a estratégia escolhida para o serviço .NET. A criação do banco, migrations, readiness e backup serão incorporados em fases posteriores do P2; esta ADR não altera o Compose atual.

### Estrutura proposta da solução

```text
services/risk-service/
├── BankCore.Risk.sln
├── src/
│   ├── BankCore.Risk.Api/
│   ├── BankCore.Risk.Application/
│   ├── BankCore.Risk.Domain/
│   └── BankCore.Risk.Infrastructure/
└── tests/
    ├── BankCore.Risk.UnitTests/
    └── BankCore.Risk.IntegrationTests/
```

- **Api:** endpoints internos, autenticação, health e mapeamento HTTP;
- **Application:** caso de uso de avaliação, regras de orquestração e contratos;
- **Domain:** decisão, score, razões e invariantes;
- **Infrastructure:** PostgreSQL/EF Core, JWT validation e persistência;
- **Tests:** regras determinísticas, contrato HTTP, PostgreSQL descartável e autenticação.

O Risk terá `/health` para liveness e `/readiness` para verificar dependências essenciais, incluindo seu próprio banco. Documentação OpenAPI, se habilitada durante desenvolvimento, não será publicada pelo gateway em ambiente production-like.

## Alternativas rejeitadas

### Escrever risco dentro de Transactions

Rejeitado: não demonstra a fronteira ASP.NET Core/C# e mistura o novo domínio com o proprietário do ledger.

### Risk acessar diretamente o banco de Transactions

Rejeitado: cria acoplamento de schema, viola ownership e torna migrations/restore mais arriscados.

### Risk escrever diretamente no ledger

Rejeitado: somente Transactions pode criar efeitos financeiros.

### Aprovar em caso de timeout

Rejeitado: uma indisponibilidade operacional não pode virar aprovação financeira.

### Introduzir Kafka ou ML nesta etapa

Rejeitado: o objetivo do P2 inicial é contrato, integração síncrona e regras determinísticas. Mensageria e ML ficam para fases posteriores.

## Consequências

Positivas:

- fronteiras de dados e responsabilidade demonstráveis;
- primeiro serviço .NET isolado sem reescrever o núcleo financeiro;
- contrato interno testável e com autenticação específica;
- replay de avaliação e falhas de integração com comportamento definido;
- evolução futura para regras mais sofisticadas sem dar acesso ao ledger.

Custos:

- um novo banco, histórico de migrations e serviço para operar;
- necessidade de compatibilizar emissão de tokens internos no Auth;
- integração síncrona adiciona latência e uma dependência de disponibilidade;
- o fluxo de idempotência de Transactions precisará de uma etapa de desenho antes da implementação.

## Não-objetivos desta ADR

- implementar C# ou criar imagens Docker;
- alterar `docker-compose.yml`, Nginx ou GitHub Actions;
- introduzir Kafka, ML, feature store ou antifraude real;
- alterar o ledger existente;
- acessar a VPS, fazer deploy ou publicar qualquer branch.
