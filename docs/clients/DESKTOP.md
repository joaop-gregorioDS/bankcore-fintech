# BankCore Desktop (Tauri)

Construir no **Windows**. Shell nativo + UI web Carbon Ledger, **cliente HTTP da API**, não necessariamente a SPA monolítica de 2.300 linhas.

## Prompt para o chat

> Leia `docs/clients/DESKTOP.md`, `API.md` e `DESIGN.md`. Scaffold Tauri 2 em `apps/desktop`. v1: login → Pix → extrato → print/PDF do comprovante. JWT em armazenamento seguro (plugin Tauri), não localStorage puro se possível.

## Notas

- Pode ser HTML/JS enxuto (telas v1 só), não copiar o `frontend/index.html` inteiro.
- Base URL configurável (`http://2.25.126.53` e `http://localhost`).
- Windows WebView2.

## Pronto quando

`tauri dev`: login demo, Pix, extrato, exportar comprovante.
