# BankCore Desktop (Tauri)

Construir no **Windows**. Shell nativo + UI web Carbon Ledger, **cliente HTTP da API**, não necessariamente a SPA monolítica de 2.300 linhas.

## Prompt para o chat

> `git pull origin main`. Leia `docs/clients/PORTFOLIO.md`, `DESKTOP.md`, `API.md` e `DESIGN.md`. Espelhe a UX do iOS. Scaffold Tauri 2 em `apps/desktop`. Cliente HTTP de `http://2.25.126.53`. v1: login → Pix → extrato → comprovante. Home viva + simulados + `version 1.10.25`. Sem empacotar `frontend/index.html`. Sem inventar endpoint. JWT em store seguro Tauri, não localStorage puro.

## Notas

- Pode ser HTML/JS enxuto (telas v1 só), não copiar o `frontend/index.html` inteiro.
- Base URL configurável (`http://2.25.126.53` e `http://localhost`).
- Windows WebView2.

## Pronto quando

`tauri dev`: login demo, Pix, extrato, exportar comprovante.
