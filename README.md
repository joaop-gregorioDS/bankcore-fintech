# 🏦 BankCore — Enterprise Web Banking & Financial Ledger

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+--009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+--3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15.0+--316192.svg?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Containerized--2496ED.svg?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![Nginx](https://img.shields.io/badge/Nginx--Reverse_Proxy--009639.svg?style=flat-square&logo=nginx&logoColor=white)](https://nginx.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.0+--38B2AC.svg?style=flat-square&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)

Plataforma de **Core Banking Corporativo (PJ) & Clientes Carbon**, desenvolvida em arquitetura de microserviços distribuídos com garantia de consistência contábil estrita (**Double-Entry Bookkeeping Ledger / Partidas Dobradas**) e ecossistema SPI BACEN (Pix).

---

## 🌦 Acesso Rápido & Demonstração

* 👊 **Web Banking (Produção):** [http://2.25.126.53](http://2.25.126.53)
* 📑 **Documentação Swagger (Transactions API):** [http://2.25.126.53/transactions/docs](https://2.25.126.53/transactions/docs)
* 🔐**Documentação Swagger (Auth API):** [http://2.25.126.53/auth/docs](http://2.25.126.53/auth/docs)

---

## ✨ Destaques de Engenharia & Funcionalidades

### 1. 💥 Livro-Razão Contábil (Double-Entry Bookkeeping)
* **Integridade Contábil Absoluta**: Nenhuma operação altera saldos isoladamente; cada débito gera o respectivo crédito na conta de liquidação bancária.
* **Idempotência com Redis**: Eliminação de transações duplicadas em caso de instabilidade de rede.
* **Exportação Contábil**: Geração de extrato em **CSV** e emissão de **Comprovantes Oficiais em PDF**.

### 2. 💠 Central Pix Completa (SPI BACEN)
* Transferências por chave CPF, e-mail e dados banários.
* **Pix de Presente** com cartões tenáticos comemorativos.
* Gestão de **Limites Diurnos e Noturnos** e chamado via **MED (Mecanismo Especial de Devolução do BACEN)**.

### 3. 🚥 Central de Pagamentos & Agenda DDA CIP
* Captura eletrônica de boletos emitidos para o CNPJ/CPF com quitação e agendamento.
* Gestão de contas em **Débito Automático** (Energia, Água, Telecomunicações).
* Gerenciador de limites para tributos federais (DARF, GPS, Simples Nacional).

### 4. 👳 Central de Cartões Carbon
* Limite Único inteligente com barra de progresso.
* Emissão de cartões virtuais e **Download da Fatura Fechada em PDF**.

### 5. 📑 Gestão de Cobranças PJ & Contratos
* Dashboard com indicadores de faturamento recebido, valores a vencer e inadimphência zero.
* Emissão de boletos e links de pagamento com QR Code Pix.

### 6. 📦 BankCore Invest & �Y Crédito Inteligente
* Plataforma de investimentos com alocação de carteira (104% do CDI com garantia do FGC).
* Simulador de crédito corporativo com cálculo de parcelas (Tabela Price e CET).

### 7. ☀️🌙 Bi-Temático & Acessibilidade
* Alternador de **Tema Claro (Banco do Brasil Gold / Clean Slate)** e **Tema Escuro (Carbon Black)**.
* Botão **A⁺ de Acessibilidade** (ampliação imediata de 112% na escala de fonte).

---

## 👧 Contas de Demonstração

| Titular | CPF | Cargo / Segmento | Saldo Inicial | Limite Carbon |
| :--- | :--- | :--- | :--- | :--- |
| **João Paulo Gregorio de Souza** | `53548376835` | CEO • Vortex Software | `R$ 18.450,80` | `R$ 50.000,00` |
| **Maria Silva Santos** | `12345678900` | CFO Т Sócia Diretora | `R$ 12.870,40` | `R$ 35.000,00` |

*Senha padrão para ambas as contas:* `teste123456`

---

## 👨‍p��� Autor

**João Paulo Gregorio de Souza**  
*Desenvolvedor Full Stack & Especialista em Arquitetura de Software*  
Empresa: **Vortex Software**
