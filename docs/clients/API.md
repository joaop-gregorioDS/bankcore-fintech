# Contrato da API BankCore

Base: `http://2.25.126.53`  
JSON, UTF-8. Rotas financeiras: header `Authorization: Bearer <access_token>`.

Sem token → **401** `{ "detail": "Token de acesso ausente." }`

## Auth (`/auth`)

### `POST /auth/login`

```json
{ "tax_id": "33548376835", "password": "teste123456" }
```

Resposta 200:

```json
{ "access_token": "eyJ...", "token_type": "bearer", "expires_in": 3600 }
```

JWT HS256, claims: `sub` (user UUID), `tax_id`, `name`, `exp`.

`tax_id` só dígitos (CPF/CNPJ).

### `POST /auth/register`

```json
{
  "tax_id": "00000000000",
  "full_name": "Nome Completo",
  "email": "pessoa@empresa.com",
  "password": "minimo8c"
}
```

201 + corpo do usuário. Depois faça login.

### `GET /auth/me`

Bearer. 200: `id`, `tax_id`, `full_name`, `email`, `is_active`, `created_at`.

### `GET /auth/directory/{tax_id}`

Bearer. Resolve CPF para Pix. 200: `{ "user_id", "tax_id", "full_name" }`. 404 se não existir.

## Contas e ledger (`/accounts`, `/transactions`)

### `POST /accounts/`

Bearer. Body `{ "user_id": "<uuid do sub do JWT>" }` — **tem que ser o mesmo `sub`**.

200/201:

```json
{
  "id": "uuid da conta",
  "user_id": "uuid do usuário",
  "account_number": "39983-0",
  "balance_reais": 16724.56,
  "is_active": true
}
```

Guarde `id` como `account_id` para depósito, Pix e extrato.

### `GET /accounts/{account_id}`

Bearer. Só a conta do usuário logado.

### `GET /accounts/{account_id}/statement`

Bearer. Lista (mais recente primeiro):

```json
{
  "transaction_id": "uuid",
  "idempotency_key": "pix_...",
  "source_account_id": "uuid|null",
  "destination_account_id": "uuid|null",
  "amount_reais": 150.0,
  "transaction_type": "TRANSFER",
  "direction": "CREDIT",
  "status": "COMPLETED",
  "created_at": "2026-09-03T20:41:08",
  "description": "Pagamento Pix Web Banking"
}
```

`direction`: `CREDIT` entrada, `DEBIT` saída. Tipos: `DEPOSIT`, `TRANSFER`.

### `POST /transactions/deposit`

```json
{
  "account_id": "<sua conta>",
  "amount_reais": 100.0,
  "idempotency_key": "dep_<uuid único>"
}
```

Gera um par DEBIT (liquidação) + CREDIT (correntista).

### `POST /transactions/pix`

```json
{
  "source_account_id": "<sua conta>",
  "destination_key": "12345678900",
  "amount_reais": 150.0,
  "idempotency_key": "pix_<uuid único>",
  "description": "Pix BankCore"
}
```

`destination_key`: CPF só dígitos (ou UUID de conta). Idempotência: **nunca** reutilize a mesma chave.

## Sequência do cliente

1. `POST /auth/login` → guardar JWT com segurança (Keychain / EncryptedPrefs / keyring).
2. `POST /accounts/` com `user_id` = `sub` → guardar `account_id` e saldo.
3. Pix / depósito com Bearer + `idempotency_key` novo.
4. Recarregar conta + statement.

## ATS / App Transport (iOS)

A demo é **HTTP** (`http://2.25.126.53`). No Info.plist: exceção ATS para esse host **somente em debug**, ou `NSAllowsArbitraryLoads` documentado como lab. Não finja HTTPS.

## Swagger

- http://2.25.126.53/auth/docs  
- http://2.25.126.53/transactions/docs  

Authorize no Swagger com o Bearer para testar.
