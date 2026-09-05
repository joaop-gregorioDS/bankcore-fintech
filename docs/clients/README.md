# Clientes BankCore

O backend (`services/`) e a SPA (`frontend/`) já existem. Três clientes do **mesmo contrato**, no mesmo monorepo, mesma API `http://2.25.126.53`.

**Estratégia e UX (ler primeiro):** [`PORTFOLIO.md`](PORTFOLIO.md) — o iOS é a referência visual; Android e Tauri se constroem no Windows a partir deste pacote no GitHub.

| Cliente | Pasta | Stack | Onde | Estado |
| :--- | :--- | :--- | :--- | :--- |
| iOS | `apps/ios` | SwiftUI, iOS 17+ | Mac M1 Air + Xcode | **Feito** `version 1.10.25` |
| Desktop | `apps/desktop` | Tauri 2 + HTML/JS Carbon Ledger | Windows | A fazer |
| Android | `apps/android` | Kotlin + Jetpack Compose | Windows (Android Studio) | A fazer |

## Ordem

1. Docs neste diretório (já no GitHub).
2. iOS no Mac — **concluído**.
3. Desktop Tauri no Windows (prova a API fora do browser).
4. Android nativo no Windows.

Um chat = um app até o happy path: **login → Pix → extrato → comprovante**, depois a home viva (grade, cartões simulados, versão).

## v1 (obrigatório em todos)

- Login das contas demo (CPF + senha) e persistência segura do JWT.
- Saldo da conta corrente (API).
- Pix por CPF (API real).
- Extrato com crédito/débito.
- Compartilhar / exportar comprovante.
- `version 1.10.25` no login e no perfil.

Fora da v1 (mock local, selo **Simulado**, iguais ao iOS / SPA): cartões, DDA, invest, crédito.

## Não fazer

- Empacotar `frontend/index.html` num WebView e chamar de app nativo.
- Copiar marca BB ou C6. Navegação/densidade sim; visual = Carbon Ledger.
- Inventar endpoints. Só o que está em `API.md`.

## Contas demo

| Titular | CPF | Senha |
| :--- | :--- | :--- |
| João Paulo | `33548376835` | `teste123456` |
| Maria Silva | `12345678900` | `teste123456` |

Base da API: `http://2.25.126.53`
