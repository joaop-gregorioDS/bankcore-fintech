# BankCore Android (Kotlin + Compose)

Construir no **Windows** com Android Studio. API: `https://bankcore.vortexsoftware.tech`.

## Prompt para o chat

> `git pull origin main`. Leia `docs/clients/PORTFOLIO.md`, `ANDROID.md`, `API.md` e `DESIGN.md`. Espelhe a UX do iOS. App Compose em `apps/android`, applicationId `br.vortex.bankcore`. API `https://bankcore.vortexsoftware.tech` (ou `http://2.25.126.53` em lab). v1: login → Pix → extrato → comprovante. Home viva + módulos simulados + `version 1.10.25`. Sem WebView da SPA. Sem inventar endpoint.

## Stack

- minSdk 26, Compose BOM atual.
- Retrofit ou Ktor + kotlinx.serialization.
- JWT no EncryptedSharedPreferences ou Android Keystore.
- Cleartext HTTP para o IP da demo (`android:usesCleartextTraffic="true"` só no flavor debug, documentado).

## Telas

Bottom nav: Início | Pix | Extrato | Cartões | Perfil. Contrato `API.md`, tokens `DESIGN.md`, UX `PORTFOLIO.md`.

## Pronto quando

Emulador ou aparelho: login Lucas, Pix para Maria, extrato com débito vermelho, share do comprovante.
