# 🏦 BankCore — Distributed Banking & Financial Ledger Engine

[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![Nginx](https://img.shields.io/badge/Nginx-Reverse_Proxy-009639?logo=nginx&logoColor=white)](https://nginx.org)

**BankCore** é um motor bancário e de livro-razão (*financial ledger*) assíncrono projetado para operações financeiras de alta concorrência com **garantia de consistência ACID**, **idempotência distribuída** e **arquitetura de microsserviços desacoplada**.

---

## 🏗️ Arquitetura do Sistema

```text
                        INTERNET
                           │
                 [ Cloudflare WAF & DDoS ]
                           │
                 [ Nginx Reverse Proxy ]
               (Port 80 / 443 SSL Termination)
                           │
               ┌───────────┴───────────┐
               ▼                       ▼
    [ Auth Microservice ]    [ Transactions & Ledger ]
       (FastAPI: 8000)            (FastAPI: 8001)
               │                       │
               ├───────────────────────┤
               ▼                       ▼
      [ PostgreSQL 16 ]           [ Redis 7 ]
   (ACID & Row Locks)       (Idempotency & Locks)

   💎 Diferenciais de Engenharia Financeira
1. 🧮 Integridade Contábil e Valores em Centavos (balance_cents)
Nenhum cálculo monetário utiliza ponto flutuante (float), eliminando por completo problemas de arredondamento e dízimas periódicas. Todas as operações são calculadas em centavos inteiros (BigInteger).

2. 🔒 Isolamento Transacional ACID e Prevenção de Deadlocks
As transferências de fundos e Pix utilizam bloqueio pessimista de linha (SELECT FOR UPDATE). Para evitar Deadlocks sob alta concorrência de transferências simultâneas entre as mesmas contas, os bloqueios de contas de origem e destino são ordenados estritamente por ID antes da aquisição da trava.

3. ⚡ Idempotência Distribuída com Redis
Cada requisição de débito ou transferência exige uma Idempotency-Key única. Se a requisição for reenviada por instabilidade de rede, o Redis responde instantaneamente o snapshot da transação já efetuada sem executar débitos duplicados (Zero Double-Spending).

4. 📜 Livro-Razão Imutável (Double-Entry Ledger)
Cada movimentação gera um registro contábil imutável rastreável no histórico da conta com timestamp UTC e status auditável.

🚀 Microsserviços & Endpoints
🔐 1. Auth Service (/auth/docs)
POST /auth/register — Cadastro de correntista com validação de CPF/CNPJ e hashing bcrypt.
POST /auth/login — Autenticação de correntista com emissão de token JWT bancário.
GET /auth/health — Liveness & Readiness check.
💳 2. Transactions & Accounts Service (/transactions/docs)
POST /accounts/ — Criação de conta corrente vinculada ao UUID do correntista.
GET /accounts/{account_id} — Consulta de saldo e dados da conta.
GET /accounts/{account_id}/statement — Extrato bancário e auditoria do Livro-Razão.
POST /transactions/deposit — Depósito de fundos com chave de idempotência.
POST /transactions/transfer — Transferência Pix atômica entre contas correntes.
🛠️ Como Executar com Docker
bash


# 1. Clonar o Repositório
git clone https://github.com/joaop-gregorioDS/bankcore-fintech.git
cd bankcore-fintech
# 2. Criar a Rede Docker Global
docker network create web_gateway
# 3. Subir os Microsserviços
docker compose up -d --build
👨‍💻 Autor
João Paulo Gregorio de Souza
Desenvolvimento de Software LTDA
São Paulo - SP, Brasil