# BankCore Desktop (Tauri)

Construir no **Windows**. Shell nativo + UI web Carbon Ledger, **cliente HTTP da API**, não necessariamente a SPA monolítica de 2.300 linhas.

## Prompt para o chat

> `git pull origin main`. Leia `docs/clients/PORTFOLIO.md`, `DESKTOP.md`, `API.md` e `DESIGN.md`. Espelhe a UX do iOS. Scaffold Tauri 2 em `apps/desktop`. Cliente HTTPS de `https://bankcore.vortexsoftware.tech`. v1: login Lucas → Pix → extrato → comprovante. Home viva + simulados + `version 1.10.25`. Modo claro por padrão; escuro só no toggle do perfil. Ícone cream `#F4F1EA` + escudo ouro `#9A7B32`. Sem empacotar `frontend/index.html`. Sem inventar endpoint. JWT em store seguro Tauri, não localStorage puro.

## Notas

- Pode ser HTML/JS enxuto (telas v1 só), não copiar o `frontend/index.html` inteiro.
- Base URL: `https://bankcore.vortexsoftware.tech` (localhost só em dev local).
- Windows WebView2.
- Tema: **claro padrão** (`html` com a paleta cream da SPA). Dark só com classe/toggle persistido.
- Ícone do `.exe` / tray: cream + escudo ouro, a partir de `apps/ios/.../AppIcon.png`.

## Pronto quando

`tauri dev`: login demo, Pix, extrato, exportar comprovante.
