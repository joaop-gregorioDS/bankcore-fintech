# BankCore

Web banking corporativo de **demonstração** — FastAPI, PostgreSQL, Redis e um ledger de partidas dobradas.

**Isto não é um banco real e não se conecta ao SPI/DICT do BACEN.** Login, saldo, Pix interno, extrato e comprovante gravam no ledger. Cartões, DDA, investimentos e crédito são simulação de interface.

[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192.svg?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

---

## Demonstração

O modo de demonstração é controlado por `DEMO_MODE` e permanece desativado por padrão. Para uma execução local explicitamente demonstrativa, defina `DEMO_MODE=true` no `.env`; essa opção habilita os seeds de demonstração e o depósito de teste. Com `DEMO_MODE=false` ou sem `.env`, nenhum usuário/conta demo é criado e o endpoint de depósito demo responde **404**.

- **Web:** [https://bankcore.vortexsoftware.tech](https://bankcore.vortexsoftware.tech)
- **Institucional:** [https://vortexsoftware.tech](https://vortexsoftware.tech)

Clientes nativos (iOS, Android e desktop) apontam para a mesma API HTTPS.

### Contas de um clique

| Titular | CPF | Senha |
| :--- | :--- | :--- |
| Lucas Mendes Rocha | `98765432100` | `teste123456` |
| Maria Silva Santos | `12345678900` | `teste123456` |

**Caminho do avaliador:** login → Pix de R$ 1,00 para o CPF da outra conta → extrato → comprovante. Também é possível abrir conta com um CPF novo e Pixar para Lucas ou Maria.

Rotas financeiras exigem JWT. Sem token, `POST /accounts/` e `POST /transactions/*` respondem **401**; o depósito de demonstração também exige `DEMO_MODE=true`.

---

## Real vs simulado

| Real (grava no ledger) | Simulado (só UX) |
| :--- | :--- |
| Cadastro, login, JWT | Cartões e fatura |
| Conta corrente e saldo | Agenda DDA, boletos |
| Pix interno por CPF | QR, limites Pix |
| Extrato e comprovante | Invest e crédito |

---

## Ledger

Implementação em `services/transactions-service/app/services/ledger.py`. Detalhe: [`docs/LEDGER.md`](docs/LEDGER.md).

- Valores em **centavos** (`BIGINT`); a API expõe reais só na borda.
- Cada Pix ou depósito gera um par DEBIT + CREDIT no mesmo `COMMIT`.
- Saldo em cache na conta; a trilha auditável é o razão.
- `SELECT … FOR UPDATE` nas contas, ordenadas por UUID.
- Idempotência: registro escopado, fingerprint determinístico e constraint única no Postgres.

---

## Código

```
frontend/                   SPA
apps/ios                    cliente iOS
apps/android                cliente Android
apps/desktop                cliente desktop
services/auth-service       correntistas, JWT, diretório Pix
services/transactions-service  contas, Pix, extrato, partidas dobradas
infra/nginx                 gateway
```

Stack: Python 3.12.8 · FastAPI · SQLAlchemy 2.0.35 · PostgreSQL 16.4 · Redis 7.4.1 · Nginx unprivileged 1.27.1.

Segredos e material criptográfico ficam fora do Git: o segredo de bootstrap e demais configurações sensíveis ficam no `.env` (não versionado), enquanto a chave privada JWT e o diretório de chaves públicas usam os caminhos configurados por `JWT_PRIVATE_KEY_FILE` e `JWT_PUBLIC_KEYS_HOST_DIR`. O Auth assina com a chave privada; os demais serviços recebem somente chaves públicas.

### Runtime local

O `docker-compose.yml` é production-like por padrão: executa os serviços de aplicação como non-root, sem `--reload`, com rede interna e apenas o Nginx publicado.

O schema não é criado pela aplicação. Execute as migrations explicitamente antes de subir os serviços:

```bash
docker compose --profile migration run --rm migrate-auth
docker compose --profile migration run --rm migrate-transactions
docker compose up -d --wait
```

Auth e Transactions possuem históricos Alembic independentes. O runner classifica o banco vazio, legado pré-P0 ou compatível pós-P0; schemas desconhecidos abortam sem alteração.

Para desenvolvimento com hot reload, use explicitamente o override:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Testes reproduzíveis

A suíte oficial não depende de PostgreSQL, pytest ou chaves JWT instalados no host. O runner cria um PostgreSQL descartável com dois bancos de teste, aplica os dois históricos Alembic, gera chaves temporárias dentro do container e remove volumes, rede e containers ao terminar:

```powershell
.\scripts\test.ps1 -Suite all
```

No Linux/macOS:

```bash
bash scripts/test.sh all
```

Suítes disponíveis: `unit`, `security`, `integration`, `postgres` e `all`. A URL usada pelos testes exige `BANKCORE_TESTING=true`, host local ou `postgres-test` e banco iniciado por `bankcore_test_`; URLs de desenvolvimento/produção são recusadas antes da migração.

Para verificar deliberadamente o caminho de falha e teardown, use `.\scripts\test.ps1 -ForceFailure`; o comando deve retornar código diferente de zero e remover o ambiente temporário.

### Backup e restore local

O fluxo P1-D valida backups PostgreSQL separados para Auth e Transactions em
containers descartáveis. Ele usa `pg_dump`/`pg_restore` dentro do ambiente
PostgreSQL, restaura em bancos vazios, compara dados financeiros e rejeita
adulteração ou alvos que não sejam explicitamente `bankcore_test_`:

```powershell
.\scripts\backup-restore.ps1
```

O manifest contém apenas metadados e SHA-256. Redis não é fonte da verdade
financeira; a fonte autoritativa é o PostgreSQL e seu ledger. O fluxo não acessa
a VPS e remove containers, volumes e artefatos temporários ao terminar.

---

## Licença

MIT © Vortex Software LTDA
