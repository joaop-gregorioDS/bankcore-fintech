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

1. `idempotency_records` vincula usuário, conta, operação e chave com unique composto.
2. O fingerprint SHA-256 cobre o contexto servidor e os campos relevantes do payload.
3. `PROCESSING` e `COMPLETED` são confirmados na mesma transação Postgres do ledger.
4. Replay idêntico retorna a transação original; payload divergente responde `409 Conflict`.
5. Falhas fazem rollback do registro e não deixam transação fantasma.

As migrations versionadas ficam em `infra/postgres/alembic/transactions/`.

## Autenticação

- Auth emite JWT RS256 com `kid`, `sub`, `iss`, `aud`, `iat`, `nbf`, `exp` e `jti`.
- O serviço de transações valida com chaves públicas rotacionáveis; a chave privada não sai do Auth. Sem Bearer → 401.
- Pix resolve uma chave exata no diretório interno com um token de serviço e recebe somente o identificador do destinatário. A chave vai no corpo da requisição, não na URL. O JWT do correntista não é reutilizado entre serviços.

## Fora do ledger

Fatura de cartão, DDA, boleto, CDB e empréstimo não liquidam no razão. São módulos de interface, com selo de simulação.

## Centavos

Valores persistidos em `BIGINT` de centavos. Requests monetários entram como `Decimal`, aceitam no máximo duas casas decimais e respeitam o teto de negócio de `R$ 999.999.999.999,99`, muito abaixo do limite de `BIGINT`. A conversão para centavos é explícita na borda; o ledger opera somente com inteiros. Respostas mantêm o número JSON legado para compatibilidade dos clientes, com conversão explícita apenas na saída HTTP.
