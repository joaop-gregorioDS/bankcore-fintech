# BankCore Android (Kotlin + Compose)

Construir no **Windows** com Android Studio. API: `http://2.25.126.53`.

## Prompt para o chat

> Leia `docs/clients/ANDROID.md`, `API.md` e `DESIGN.md`. Implemente o app em `apps/android` (Compose). v1: login → Pix → extrato → comprovante. Sem WebView da SPA.

## Stack

- minSdk 26, Compose BOM atual.
- Retrofit ou Ktor + kotlinx.serialization.
- JWT no EncryptedSharedPreferences ou Android Keystore.
- Cleartext HTTP para o IP da demo (`android:usesCleartextTraffic="true"` só no flavor debug, documentado).

## Telas

Bottom nav: Início | Pix | Extrato. Mesmo contrato e tokens de `DESIGN.md` / `API.md`.

## Pronto quando

Emulador ou aparelho: login João, Pix para Maria, extrato com débito vermelho, share do comprovante.
