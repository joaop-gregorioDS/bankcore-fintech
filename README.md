# BankCore — Web Banking de Demonstração

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192.svg?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)

Demo de **web banking corporativo (PJ)** para portfólio: um avaliador abre a URL, entra em um clique e opera saldo, Pix interno, depósito e extrato contra um ledger com partidas dobradas, lock pessimista e idempotência.

Isto **não** é um core conectado ao SPI/DICT do BACEN nem um banco real. Cartões, DDA, MED, boletos, invest e crédito são **simulação de interface** (módulos didáticos na SPA).

---

## Acesso

* Demo: [http://2.25.126.53](http://2.25.126.53)
* Swagger Auth: [http://2.25.126.53/auth/docs](http://2.25.126.53/auth/docs)
* Swagger Ledger: [http://2.25.126.53/transactions/docs](http://2.25.126.53/transactions/docs)

Ambiente HTTP de laboratório (IP da VPS, sem TLS).

### Contas de demonstração

| Titular | CPF | Senha | Saldo inicial (seed) |
| :--- | :--- | :--- | :--- |
| João Paulo Gregorio de Souza | `33548376835` | `teste123456` | R$ 18.450,80 |
| Maria Silva Santos | `12345678900` | `teste123456` | R$ 12.870,40 |

Contas já existentes na VPS **não** são sobrescritas pelo seed.

Dá para **Abrir Conta Carbon** com outro CPF: o cadastro chama a API, cria a conta no ledger e permite Pix para João/Maria.

---

## O que o avaliador opera de verdade

| Operação | Onde | Efeito |
| :--- | :--- | :--- |
| Login / register | `POST /auth/login`, `POST /auth/register` | JWT HS256 |
| Conta corrente | `POST /accounts/` (Bearer) | Cria ou devolve a conta do `sub` do token |
| Depósito | `POST /transactions/deposit` | Débito na conta de liquidação + crédito no correntista |
| Pix por CPF | `POST /transactions/pix` | Diretório interno `GET /auth/directory/{cpf}` — **sem** senha do destino |
| Extrato, CSV, PDF | `GET /accounts/{id}/statement` | Cabeçalho da transação + direção CREDIT/DEBIT |

Rotas financeiras **exigem JWT**. Request sem token → 401.

### O que é simulação de UX

Central de Cartões, DDA CIP, boletos, débitos automáticos, Pix de presente, MED BACEN, limites Pix, cobranças PJ, BankCore Invest e o simulador Price **não gravam no ledger**. A UI deixa isso explícito.

---

## Engenharia do ledger (o que defender em entrevista)

1. **Centavos inteiros** (`BIGINT`). Nada de `float` para dinheiro.
2. **Partidas dobradas:** cada operação gera um par `ledger_entries` (DEBIT + CREDIT) de mesmo valor. Depósito: débito na conta de liquidação interna `00000-0`, crédito no correntista. Pix: débito origem, crédito destino. \(\sum\) débitos \(=\) \(\sum\) créditos.
3. **Saldo em `accounts.balance_cents`** é cache atualizado **na mesma transação** das entradas. Fonte auditável = o razão.
4. **ACID + `SELECT … FOR UPDATE`** nas contas envolvidas, em ordem de UUID, para evitar deadlock e gasto duplo.
5. **Idempotência em duas camadas:** `SET idem:{key} NX EX 86400` no Redis e `idempotency_key` unique no Postgres (`IntegrityError` devolve a transação existente).
6. **Pix interno:** o CPF é resolvido no Auth Service com o JWT do remetente. Não há login com senha fixa no destino.

Stack: FastAPI (async) + SQLAlchemy 2 + asyncpg + PostgreSQL 16 + Redis 7 + Nginx + SPA Vanilla JS / Tailwind.

```
Navegador → Nginx :80
              ├─ /                 frontend/index.html
              ├─ /auth/*           auth-service :8000
              └─ /transactions/*, /accounts/*   transactions-service :8001
                    ├─ PostgreSQL  (bankcore_auth | bankcore_transactions)
                    └─ Redis       (chaves de idempotência)
```

---

## Rodar local

```bash
cp .env.example .env
docker compose up -d --build
```

Abra `http://localhost`. Na VPS que já usa Nginx do host na rede `web_gateway`:

```bash
docker compose -f docker-compose.yml -f docker-compose.vps.yml up -d --build
```

**Segredos:** o histórico do Git já publicou senha antiga de Postgres/JWT. Na VPS, gere valores novos em `.env` e **não** reuse `bankcore_secret_password_2026` / `super_secret_jwt_key_bankcore_production_2026`.

---

## Autor

**João Paulo Gregorio de Souza**  
Vortex Software
