# BankCore — sessão (Mac iOS + handoff Windows)

Atualizado em 2026-09-05.

## Estratégia

A maneira adequada de construir Android e Tauri: **GitHub como fonte da verdade**. No Windows, `git pull` e ler `docs/clients/PORTFOLIO.md`. Um chat = um app. iOS é a referência de UX. Não colar o histórico deste chat no Windows.

- Estratégia: [`docs/clients/PORTFOLIO.md`](docs/clients/PORTFOLIO.md)
- Contrato: [`docs/clients/API.md`](docs/clients/API.md)
- Tokens: [`docs/clients/DESIGN.md`](docs/clients/DESIGN.md)

Ordem: **Tauri** (`apps/desktop`) → **Android** (`apps/android`).

## Git

- Repo: `/Users/joaopaulogregorio/bankcore-fintech`
- Remote: `https://github.com/joaop-gregorioDS/bankcore-fintech`
- Branch: `main`
- iOS no GitHub: `4a6f9f0` — `feat(ios): home viva, ícone do escudo e version 1.10.25`

## iOS (este Mac)

- Pasta: `apps/ios/BankCore.xcodeproj`
- Bundle: `br.vortex.bankcore`
- Versão: **1.10.25** (build 11025)
- API: `http://2.25.126.53`
- JWT no Keychain; Pix/extrato reais; cartões/DDA/invest simulados
- Aparelho: iPhone 11 Pro Max (Signing → Team; confiar certificado na primeira instalação)

Contas: João `33548376835` / Maria `12345678900` / `teste123456`.

## Windows (próximos chats)

Prompts prontos em `docs/clients/PORTFOLIO.md` (seção “Prompts para colar no Windows”).

1. `git clone` ou `git pull origin main`
2. Chat Tauri: ler PORTFOLIO + DESKTOP + API + DESIGN → `apps/desktop`
3. Chat Android: ler PORTFOLIO + ANDROID + API + DESIGN → `apps/android`

## Retomar este chat no Mac

Grok TUI: `/resume` — sessão `01a0693e-ea0c-7132-adc7-63565813fec4` (cwd home).

Prompt se o `/resume` não estiver à mão:

> Continue BankCore em ~/bankcore-fintech. Leia SESSION.md e docs/clients/PORTFOLIO.md. iOS 1.10.25 já está no GitHub (4a6f9f0). Android e Tauri são no Windows.
