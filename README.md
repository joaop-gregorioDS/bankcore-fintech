# BankCore

Web banking corporativo de **demonstração** — FastAPI, PostgreSQL, Redis e um ledger de partidas dobradas.

**Isto não é um banco real e não se conecta ao SPI/DICT do BACEN.** Login, saldo, Pix interno, extrato e comprovante gravam no ledger. Cartões, DDA, investimentos e crédito são simulação de interface.

[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192.svg?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

---

## Demonstração

- **Web:** [https://bankcore.vortexsoftware.tech](https://bankcore.vortexsoftware.tech)
- **Institucional:** [https://vortexsoftware.tech](https://vortexsoftware.tech)

Clientes nativos (iOS, Android e desktop) apontam para a mesma API HTTPS.

### Contas de um clique

| Titular | CPF | Senha |
| :--- | :--- | :--- |
| Lucas Mendes Rocha | `98765432100` | `teste123456` |
| Maria Silva Santos | `12345678900` | `teste123456` |

**Caminho do avaliador:** login → Pix de R$ 1,00 para o CPF da outra conta → extrato → comprovante. Também é possível abrir conta com um CPF novo e Pixar para Lucas ou Maria.

Rotas financeiras exigem JWT. Sem token, `POST /accounts/` e `POST /transactions/*` respondem **401**.

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
- Idempotência: Redis `NX` + unique no Postgres.

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

Stack: Python 3.12 · FastAPI · SQLAlchemy 2 · PostgreSQL 16 · Redis 7 · Nginx.

Segredos ficam no `.env` (não versionado).

---

## Licença

MIT © Vortex Software LTDA
