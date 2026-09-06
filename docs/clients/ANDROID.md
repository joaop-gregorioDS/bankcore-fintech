# BankCore Android (Kotlin + Compose)

Construir no **Windows** com Android Studio. API: `https://bankcore.vortexsoftware.tech`.

## Prompt para o chat

> `git pull origin main`. Leia `docs/clients/PORTFOLIO.md`, `ANDROID.md`, `API.md` e `DESIGN.md`. Espelhe a UX do iOS. App Compose em `apps/android`, applicationId `br.vortex.bankcore`. API `https://bankcore.vortexsoftware.tech`. v1: login Lucas → Pix → extrato → comprovante. Home viva + simulados + `version 1.10.25`. Modo claro por padrão; escuro só no toggle do perfil. Launcher cream `#F4F1EA` + escudo ouro `#9A7B32`. Sem WebView da SPA. Sem inventar endpoint.

## Stack

- minSdk 26, Compose BOM atual.
- Retrofit ou Ktor + kotlinx.serialization.
- JWT no EncryptedSharedPreferences ou Android Keystore.
- HTTPS oficial. Cleartext só no flavor debug se cair no IP `2.25.126.53`.
- Tema: **claro padrão** (`#F4F1EA`). Dark via toggle persistido (DataStore), não pelo tema do sistema no primeiro launch.
- Ícone: copiar `apps/ios/BankCore/Assets.xcassets/AppIcon.appiconset/AppIcon.png` (cream + ouro).

## Telas

Bottom nav: Início | Pix | Extrato | Cartões | Perfil. Contrato `API.md`, tokens `DESIGN.md`, UX `PORTFOLIO.md`.

## Pronto quando

Emulador ou aparelho: login Lucas, Pix para Maria, extrato com débito vermelho, share do comprovante.
