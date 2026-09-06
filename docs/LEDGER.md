# Ledger BankCore

O que o runtime implementa. Não é SPI/DICT/BACEN.

## Partidas dobradas

Cada depósito ou Pix grava duas linhas em `ledger_entries` (DEBIT + CREDIT) com o mesmo `amount_cents`, na mesma transação Postgres de `ledger_transactions`.

- Depósito: débito na conta de liquidação interna + crédito no correntista.
- Pix: débito na origem + crédito no destino.

`accounts.balance_cents` é cache atualizado no mesmo `COMMIT`. O razão é a trilha auditável.

## Concorrência

`SELECT … FOR UPDATE` nas contas envolvidas, ordenadas por UUID, para dois Pix paralelos não lerem o mesmo saldo.

## Idempotência

1. Redis `SET idem:{key} NX EX 86400`
2. Unique em `ledger_transactions.idempotency_key`
3. Se a operação falha, a chave Redis é liberada para retry

## Autenticação

- Auth emite JWT HS256 (`sub`, `tax_id`, `name`, `exp`).
- O serviço de transações valida o mesmo segredo. Sem Bearer → 401.
- Pix resolve CPF no diretório com o JWT do **remetente**. Não há login com a senha do destino.

## Fora do ledger

Fatura de cartão, DDA, boleto, CDB e empréstimo não liquidam no razão. São módulos de interface, com selo de simulação.

## Centavos

Valores em `BIGINT`. A API expõe `amount_reais` apenas na borda (`/ 100.0`).
