# BankCore — o que o código realmente faz (entrevista)

Use isto junto com o guia de estudos. As respostas abaixo apontam para arquivos, não para o README antigo.

## Partidas dobradas

Cada depósito/Pix grava **duas** linhas em `ledger_entries` (DEBIT + CREDIT) com o mesmo `amount_cents`, na mesma transação Postgres do header `ledger_transactions`.

- Depósito: débito em `accounts` `00000-0` (liquidação interna) + crédito no correntista.
- Pix: débito na origem + crédito no destino.
- Implementação: `services/transactions-service/app/services/ledger.py` (`_apply_entries`, `_balanced`).

`accounts.balance_cents` é **cache** atualizado no mesmo `COMMIT`. O razão é a trilha auditável.

## Concorrência e gasto duplo

`SELECT … FOR UPDATE` nas contas envolvidas, ordenadas por UUID (`_lock_accounts`). Sem isso, dois Pix paralelos leriam o mesmo saldo.

## Idempotência

1. Redis `SET idem:{key} NX EX 86400`
2. Unique `ledger_transactions.idempotency_key` — `IntegrityError` devolve a transação já gravada
3. Se a operação falha, a chave Redis é apagada para o retry ser possível

O frontend envia `idempotency_key` no body (`pix_` / `dep_` + timestamp).

## Autenticação

- Auth emite JWT HS256 (`sub`, `tax_id`, `name`, `exp`).
- Transactions **valida** o mesmo secret (`app/deps.py`). Sem Bearer → 401.
- Pix resolve CPF em `GET /auth/directory/{tax_id}` com o JWT do **remetente**. Não há login com senha do destino.

## O que NÃO está no runtime

SPI BACEN, DICT, MED, DDA CIP, fatura de cartão, boleto, CDB e empréstimo **não** liquidam no ledger. São módulos didáticos da SPA (selo “Simulado”).

## Centavos

Valores em `BIGINT` (`balance_cents`, `amount_cents`). A API expõe `amount_reais` só na borda (`/ 100.0`).
