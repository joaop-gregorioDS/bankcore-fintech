# BankCore

Web banking corporativo de **demonstração** — FastAPI, PostgreSQL, Redis e um ledger de partidas dobradas. Feito para portfólio: o avaliador entra em um clique, envia Pix, lê o extrato e baixa o comprovante em PDF.

**Isto não é um banco real e não se conecta ao SPI/DICT do BACEN.** O núcleo financeiro (login, saldo, depósito, Pix interno, extrato) é API de verdade. Cartões, DDA, MED, boletos, investimentos e crédito são simulação de interface, com dados mock só para a tela parecer viva.

[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192.svg?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

---

## Demonstração

- App: [http://2.25.126.53](http://2.25.126.53)
- Auth API: [http://2.25.126.53/auth/docs](http://2.25.126.53/auth/docs)
- Ledger API: [http://2.25.126.53/transactions/docs](http://2.25.126.53/transactions/docs)

Ambiente de laboratório em HTTP (IP da VPS).

### Contas de um clique

| Titular | CPF | Senha |
| :--- | :--- | :--- |
| João Paulo Gregorio de Souza | `33548376835` | `teste123456` |
| Maria Silva Santos | `12345678900` | `teste123456` |

**Caminho do avaliador (2 minutos):** login → Pix para o CPF da outra conta → extrato → comprovante PDF. Também dá para **Abrir conta** com um CPF novo e Pixar para João ou Maria.

Rotas financeiras exigem JWT. Sem token, `POST /accounts/` e `POST /transactions/*` respondem **401**.

---

## O que é real e o que é simulado

| Real (grava no ledger) | Simulado (só UX / mock) |
| :--- | :--- |
| Cadastro, login, JWT | Central de cartões e fatura |
| Conta corrente e saldo | Agenda DDA, boletos, débitos automáticos |
| Depósito | Pix de presente, QR, limites Pix, MED |
| Pix interno por CPF | Cobranças PJ |
| Extrato, comprovante PDF, extrato PDF | BankCore Invest e crédito (Tabela Price) |

---

## Arquitetura

```
Navegador
    │
    ▼
Nginx (porta 80)
    ├─ /                         SPA  (frontend/index.html)
    ├─ /auth/*                   auth-service        :8000
    └─ /transactions/*  /accounts/*   transactions-service :8001
              │                              │
              ▼                              ▼
        PostgreSQL                    PostgreSQL + Redis
        bankcore_auth                 bankcore_transactions
                                      idempotência NX + razão
```

| Peça | Papel |
| :--- | :--- |
| `services/auth-service` | Correntistas, bcrypt, JWT, diretório de CPF (`GET /auth/directory/{tax_id}`) |
| `services/transactions-service` | Contas, depósito, Pix, extrato, partidas dobradas |
| `frontend/index.html` | SPA Vanilla JS + Tailwind (tema Carbon Ledger) |
| `infra/nginx/bankcore.conf` | Proxy e estáticos |
| `docker-compose.yml` | Stack local |
| `docker-compose.vps.yml` | Overlay: junta os serviços à rede `web_gateway` da VPS |

---

## Ledger (o que o código faz)

Implementação em `services/transactions-service/app/services/ledger.py`. Detalhe: [`docs/LEDGER.md`](docs/LEDGER.md).

1. **Centavos inteiros** (`BIGINT`). A API só converte para reais na borda.
2. **Partidas dobradas.** Cada operação gera um par `ledger_entries` (DEBIT + CREDIT) do mesmo valor.
   - Depósito: débito na conta de liquidação `00000-0`, crédito no correntista.
   - Pix: débito na origem, crédito no destino.
3. **Saldo em cache.** `accounts.balance_cents` atualiza no mesmo `COMMIT` das entradas. A trilha auditável é o razão.
4. **Concorrência.** `SELECT … FOR UPDATE` nas contas, ordenadas por UUID (anti-deadlock, anti gasto-duplo).
5. **Idempotência em duas camadas.** Redis `SET idem:{key} NX EX 86400` e unique no Postgres; em falha a chave Redis é liberada.
6. **Pix interno.** O CPF do destino é resolvido no Auth com o JWT do **remetente**. Não há login com senha do destinatário.

---

## Interface

Paleta **Carbon Ledger**: preto / ivory / ouro (acento) / vermelho só em saídas. Tipografia contida, um CTA ouro por tela.

Comprovante e extrato em PDF saem em papel cream, coerentes com a página — com aviso explícito de documento de demonstração (não é SPI/BACEN).

---

## Stack

Python 3.12 · FastAPI (async) · SQLAlchemy 2 · asyncpg · PostgreSQL 16 · Redis 7 · Nginx · Vanilla JS · Tailwind CSS (CDN)

---

## Rodar local

```bash
git clone https://github.com/joaop-gregorioDS/bankcore-fintech.git
cd bankcore-fintech
cp .env.example .env
docker compose up -d --build
```

Abra `http://localhost`.

Na VPS que já usa o Nginx `central-nginx-proxy` na rede `web_gateway`:

```bash
cp .env.example .env          # senha do Postgres = a do volume existente
export GATEWAY_PORT=8080      # não disputa a porta 80 com o proxy do host
docker compose -f docker-compose.yml -f docker-compose.vps.yml up -d --build
```

Segredos ficam no `.env` (não versionado). Use valores próprios; o histórico público do Git já teve credenciais de exemplo.

---

## Estrutura

```
frontend/                 SPA
services/auth-service/    autenticação e diretório Pix
services/transactions-service/
  app/services/ledger.py  partidas dobradas, lock, idempotência
infra/nginx/              conf do gateway
docs/LEDGER.md            mapa afirmação → arquivo (ledger, JWT, Pix)
```

---

## Licença

MIT © João Paulo Gregorio de Souza · Vortex Software
