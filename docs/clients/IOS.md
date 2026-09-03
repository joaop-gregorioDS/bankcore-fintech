# BankCore iOS (SwiftUI) — Mac M1 Air

Construir **neste Mac**, não no Windows. O backend já está em `http://2.25.126.53`.

## Prompt para o chat no Mac

> Clone `https://github.com/joaop-gregorioDS/bankcore-fintech`. Leia `docs/clients/IOS.md`, `docs/clients/API.md` e `docs/clients/DESIGN.md`. Implemente o app nativo SwiftUI em `apps/ios` (Xcode). Cliente da API containerizada. v1: login → Pix → extrato → comprovante. Não use WKWebView da SPA. Não invente endpoints.

## Setup na máquina

1. Xcode atual (iOS 17+).
2. Clone o monorepo (ou `git pull` se já clonou):

```bash
git clone https://github.com/joaop-gregorioDS/bankcore-fintech.git
cd bankcore-fintech
```

3. Crie o projeto em `apps/ios` (Xcode → App → SwiftUI, bundle `br.vortex.bankcore`).
4. Info.plist: HTTP permitido para `2.25.126.53` (ATS exception de laboratório).

## Arquitetura sugerida

```
apps/ios/BankCore/
  App/                 # @main, AppState
  Networking/          # APIClient, JWT, models Codable
  Features/
    Login/
    Home/
    Pix/
    Statement/
    Receipt/
  Design/              # Color tokens Carbon Ledger
```

- `URLSession` + `async/await`.
- JWT no **Keychain**, não no UserDefaults.
- `account_id` em memória após `POST /accounts/`.
- `idempotency_key`: `UUID().uuidString` prefixado (`pix_`, `dep_`).

## Telas

Tab bar: Início | Pix | Extrato.

- Login: dois botões demo (João / Maria) + formulário.
- Início: saldo `balance_reais`, botão ouro Pix.
- Pix: `destination_key` = CPF dígitos, valor Decimal, confirmação.
- Extrato: `direction` DEBIT vermelho, CREDIT texto padrão.
- Comprovante: ShareLink + texto/PDF local (não precisa html2pdf).

## Pronto quando

- Simulador iPhone: login João, Pix R$ 1,00 para `12345678900`, aparece no extrato dos dois lados (João débito, Maria crédito se logar nela).
- Sem token, a API 401 (o app nem chama sem JWT).
- Visual Carbon Ledger, não um clone de marca de banco.

## Fora de escopo neste chat

Tauri, Android, alterar o backend, WebView da SPA.
