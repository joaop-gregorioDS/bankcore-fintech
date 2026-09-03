# Clientes BankCore

O backend (`services/`) e a SPA (`frontend/`) já existem. Estes documentos definem **três clientes** do mesmo contrato, no mesmo monorepo.

| Cliente | Pasta | Stack | Onde construir |
| :--- | :--- | :--- | :--- |
| Desktop | `apps/desktop` | Tauri 2 + HTML/JS (Carbon Ledger) | Windows |
| Android | `apps/android` | Kotlin + Jetpack Compose | Windows (Android Studio) |
| iOS | `apps/ios` | SwiftUI, iOS 17+ | **Mac M1 Air + Xcode** |

## Ordem

1. Este pacote de docs (já neste diretório).
2. Desktop Tauri (prova a API fora do browser).
3. Android nativo.
4. iOS nativo **no Mac** — clone o repo, leia `IOS.md` + `API.md` + `DESIGN.md`, implemente em `apps/ios`.

Um chat = um app até o happy path: **login → Pix → extrato → comprovante**.

## v1 (obrigatório em todos)

- Login das contas demo (CPF + senha) e persistência segura do JWT.
- Saldo da conta corrente.
- Pix por CPF (API real).
- Extrato com crédito/débito.
- Compartilhar / exportar comprovante.

Fora da v1 (mock local opcional, igual à SPA): cartões, DDA, MED, invest, crédito.

## Não fazer

- Empacotar `frontend/index.html` num WebView e chamar de app nativo (iOS/Android).
- Copiar marca C6. Inspiração de **navegação** (tabs, densidade); visual = Carbon Ledger.
- Inventar endpoints. Só o que está em `API.md`.

## Contas demo

| Titular | CPF | Senha |
| :--- | :--- | :--- |
| João Paulo | `33548376835` | `teste123456` |
| Maria Silva | `12345678900` | `teste123456` |

Base da API: `http://2.25.126.53`
