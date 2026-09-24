# BankCore — Fintech Platform & Multiplatform Banking Ecosystem

Plataforma fintech corporativa de demonstração — Backend de alta confiabilidade em microserviços com **FastAPI**, **PostgreSQL 16**, **Redis 7** e um **Ledger Financeiro de Partidas Dobradas (ACID)**, integrado a um ecossistema omni-channel completo: **Web Banking SPA**, **Desktop Windows (Tauri 2)**, **Android Nativo (Jetpack Compose)** e **iOS Nativo (SwiftUI)**.

Feito para portfólio de engenharia de software de ponta: o avaliador entra em um clique, transfere via Pix, consulta o razão contábil e exporta comprovantes e extratos em PDF e CSV.

> [!IMPORTANT]
> **Aviso de Demonstração Institucional:**  
> Este projeto é uma simulação de engenharia e não opera como instituição financeira real nem se conecta ao SPI/DICT do Banco Central do Brasil (BACEN). O núcleo contábil e transacional (autenticação JWT, contas, saldos em centavos, depósitos, Pix interno e extrato) opera via API real e banco de dados. Os módulos de cartões, DDA, MED, investimentos e crédito são demonstrações didáticas de UX com dados simulados.

---

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-316192.svg?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg?style=flat-square&logo=redis&logoColor=white)](https://redis.io/)
[![Tauri](https://img.shields.io/badge/Tauri-2.0-24C8D8.svg?style=flat-square&logo=tauri&logoColor=white)](https://tauri.app/)
[![Android](https://img.shields.io/badge/Android-Jetpack%20Compose-3DDC84.svg?style=flat-square&logo=android&logoColor=white)](https://developer.android.com/jetpack/compose)
[![iOS](https://img.shields.io/badge/iOS-SwiftUI-000000.svg?style=flat-square&logo=swift&logoColor=white)](https://developer.apple.com/swiftui/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

---

## 🌐 Demonstração & Ambientes Oficiais

* **Web Banking em Produção:** [https://bankcore.vortexsoftware.tech](https://bankcore.vortexsoftware.tech)
* **Auth API (Swagger Docs):** [https://bankcore.vortexsoftware.tech/auth/docs](https://bankcore.vortexsoftware.tech/auth/docs)
* **Transactions & Ledger API (Swagger Docs):** [https://bankcore.vortexsoftware.tech/transactions/docs](https://bankcore.vortexsoftware.tech/transactions/docs)
* **Website Institucional:** [https://vortexsoftware.tech](https://vortexsoftware.tech)
* *(Laboratório direto via IP: `http://2.25.126.53:8080`)*

---

### 🔑 Contas Demo de Um Clique

O sistema possui duas contas pré-configuradas no banco para teste imediato de transferências recíprocas:

| Titular | CPF (login) | Senha | Perfil & Saldo Inicial |
| :--- | :--- | :--- | :--- |
| **Lucas Mendes Rocha** | `98765432100` | `teste123456` | Vortex Carbon Black Corporate (R$ 10.000,00) |
| **Maria Silva Santos** | `12345678900` | `teste123456` | Vortex Carbon Platinum (R$ 10.000,00) |

**Fluxo do Avaliador (2 minutos):**
1. Acesse o Web Banking e clique no botão demo de **Lucas Mendes**;
2. Envie um Pix de qualquer valor para o CPF de **Maria Silva** (`12345678900`);
3. Veja o saldo debitar instantaneamente e abra o **Extrato**;
4. Clique no lançamento para gerar o **Comprovante oficial em PDF** (estilo papel ivory de segurança);
5. Alterne para a conta da Maria e verifique o crédito instantâneo correspondente.

---

## 📱 Ecossistema Multiplataforma (Omni-channel)

Todas as superfícies consomem o **mesmo contrato de API** e compartilham o design system **Carbon Ledger**:

| Superfície | Diretório | Stack Tecnológica | Formato / Distribuição | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **Web Banking** | `frontend/` | Vanilla JS moderno + Tailwind CSS | SPA servida via Nginx com HTTPS Let's Encrypt | **Produção** |
| **Desktop Windows** | `apps/desktop/` | Tauri 2 (Rust) + Vite + Store seguro | Instalador nativo NSIS (`-setup.exe`) e `.msi` | **Concluído (`v1.10.25`)** |
| **Android Nativo** | `apps/android/` | Kotlin + Jetpack Compose + Material 3 | APK nativo (minSdk 26, Android 8.0+) | **Concluído (`v1.10.25`)** |
| **iOS Nativo** | `apps/ios/` | Swift + SwiftUI (iOS 17+) | Xcode Project nativo | **Concluído (`v1.10.25`)** |

Documentação técnica específica dos clientes: [`docs/clients/README.md`](docs/clients/README.md).

---

## ⚖️ O que é Real vs. O que é Simulado

| Real (Liquidado no Ledger Contábil) | Simulado (Experiência Didática de UX / Mock) |
| :--- | :--- |
| **Autenticação:** Cadastro, login, hash Bcrypt e emissão de JWT HS256 | **Cartões:** Limite fictício, fatura e bloqueio temporário |
| **Contas Correntes:** Criação de conta e saldo persistido em centavos (`BIGINT`) | **Agenda DDA:** Boletos a pagar e agendamentos simulados |
| **Depósitos:** Crédito na conta e débito na conta de liquidação interna (`00000-0`) | **Módulos PJ:** Cobranças e emissão de carnês |
| **Pix Interno:** Resolução de chave CPF, lock transacional e transferência atômica | **Investimentos:** BankCore Invest e simulação de rentabilidade |
| **Extrato & Comprovantes:** Razão analítico, extrato em CSV/PDF e recibos | **Crédito:** Simulador de empréstimo via Tabela Price |

---

## 🏗️ Arquitetura do Sistema

```
                         ┌────────────────────────────────────────────────────────┐
                         │               CLIENTES OFICIAIS (Omni-channel)         │
                         │                                                        │
                         │  [Web SPA]   [Desktop Tauri]   [Android]   [iOS App]   │
                         └───────┬─────────────┬──────────────┬────────────┬──────┘
                                 │             │              │            │
                                 └─────────────┼──────────────┴────────────┘
                                               ▼ HTTPS / REST
                                 ┌───────────────────────────┐
                                 │       Nginx Gateway       │
                                 │  (Port 80/443 SSL Certbot)│
                                 └─────────────┬─────────────┘
                                               │
                        ┌──────────────────────┴──────────────────────┐
                        ▼                                             ▼
          ┌───────────────────────────┐                 ┌───────────────────────────┐
          │       auth-service        │                 │   transactions-service    │
          │         (FastAPI)         │                 │         (FastAPI)         │
          │                           │                 │                           │
          │  • Login / Cadastro       │  JWT Validação  │  • Ledger Partidas D多种  │
          │  • Emissão de JWT HS256   │◄────────────────┤  • Depósito & Pix         │
          │  • Diretório de Chaves CPF│                 │  • Extrato & Comprovantes │
          └─────────────┬─────────────┘                 └─────────────┬─────────────┘
                        │                                             │
                        ▼                                      ┌──────┴──────┐
          ┌───────────────────────────┐                        ▼             ▼
          │   PostgreSQL (auth_db)    │                  ┌──────────┐  ┌──────────┐
          │      Tabela: users        │                  │PostgreSQL│  │ Redis 7  │
          └───────────────────────────┘                  │(trans_db)│  │Idempotência│
                                                         └──────────┘  └──────────┘
```

---

## 💎 Mecânica do Ledger Financeiro

Os detalhes de modelagem matemática e contábil estão documentados em [`docs/LEDGER.md`](docs/LEDGER.md).

1. **Partidas Dobradas (Double-Entry Bookkeeping):**  
   Nenhum dinheiro é criado ou destruído sem contrapartida. Cada movimentação grava exatamente duas entradas (`ledger_entries`) na mesma transação atômica do banco:
   $$\sum \text{DEBIT} = \sum \text{CREDIT}$$
   * **Depósito:** Débito na conta mestre do sistema (`00000-0`) e Crédito na conta do usuário.
   * **Pix:** Débito na conta de origem e Crédito na conta de destino.
2. **Armazenamento em Centavos Inteiros (`BIGINT`):**  
   Valores financeiros nunca usam ponto flutuante (`FLOAT`/`DOUBLE`), prevenindo erros de arredondamento IEEE 754. `R$ 100,50` é armazenado estritamente como `10050`.
3. **Prevenção de Deadlocks e Gasto Duplo:**  
   As contas envolvidas são bloqueadas com `SELECT ... FOR UPDATE` ordenadas deterministicamente pelo identificador UUID. Isso elimina deadlocks em transferências simultâneas concorrentes.
4. **Idempotência em Duas Camadas:**  
   * **Borda:** Chave de idempotência no Redis via `SET idem:{key} NX EX 86400`. Se a requisição falhar prematuramente, a chave é liberada para retry.
   * **Persistência:** Restrição única (`UNIQUE`) no PostgreSQL na coluna `ledger_transactions.idempotency_key`.

---

## 🎨 Design System: Carbon Ledger

* **Paleta Nobre:** Preto Carbono (`#0B0B0C`), Fundo Cream Ivory (`#F4F1EA`), Acento Ouro Nobre (`#9A7B32`) e Vermelho Débito (`#B42318`).
* **Modo Claro por Padrão:** Segue a elegância institucional das instituições bancárias privadas; modo escuro ativável por toggle no perfil.
* **Comprovantes de Papel Ivory:** Geração dinâmica de comprovantes com hash de autenticação digital (`AUT-{IDEMPOTENCY}`) e layout padronizado para impressão e download.

---

## 📂 Estrutura do Repositório

```text
bankcore-fintech/
├── apps/
│   ├── android/            # Cliente nativo Kotlin + Jetpack Compose
│   ├── desktop/            # Cliente nativo Tauri 2 (Rust + Vite + NSIS)
│   └── ios/                # Cliente nativo Swift + SwiftUI (Xcode)
├── frontend/               # SPA Web Banking (HTML5, Vanilla JS, Tailwind CSS)
├── services/
│   ├── auth-service/       # Microsserviço de autenticação, JWT e diretório CPF
│   └── transactions-service/# Microsserviço financeiro, ledger e partidas dobradas
├── infra/
│   └── nginx/              # Configurações do Nginx Gateway e proxy reverso
├── docs/
│   ├── LEDGER.md           # Especificação detalhada da mecânica contábil
│   └── clients/            # Especificações de design, API e arquitetura dos apps
├── docker-compose.yml      # Orquestração local de desenvolvimento
├── docker-compose.vps.yml  # Configuração de deploy em produção na VPS
└── README.md
```

---

## 🚀 Como Executar Localmente

### Pré-requisitos
* [Docker](https://www.docker.com/) e Docker Compose instalados.

### 1. Backend e Web Banking (Docker)

```bash
# Clone o repositório
git clone https://github.com/joaop-gregorioDS/bankcore-fintech.git
cd bankcore-fintech

# Copie as variáveis de ambiente de exemplo
cp .env.example .env

# Suba todos os microsserviços e bancos de dados
docker compose up -d --build
```

Acesse no seu navegador:
* **Web Banking:** [http://localhost](http://localhost)
* **Swagger Auth:** [http://localhost/auth/docs](http://localhost/auth/docs)
* **Swagger Transactions:** [http://localhost/transactions/docs](http://localhost/transactions/docs)

### 2. Desktop Windows (Tauri 2)

```bash
cd apps/desktop
npm install
npm run tauri dev
```
Para gerar o instalador Windows NSIS (`-setup.exe`):
```bash
npm run bundle
```

### 3. Android Nativo (Jetpack Compose)

Abra a pasta `apps/android` no **Android Studio** ou compile via terminal:
```bash
cd apps/android
./gradlew assembleDebug
```

---

## 📄 Licença

Distribuído sob a licença MIT. Consulte [`LICENSE`](LICENSE) para mais informações.

Desenvolvido por **Vortex Software LTDA** — [https://vortexsoftware.tech](https://vortexsoftware.tech)
