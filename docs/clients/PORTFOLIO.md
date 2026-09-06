# BankCore — estratégia dos clientes (portfólio)

Como construir **Android** e **Tauri** iguais ao iOS, todos contra a **mesma API** na VPS. Este arquivo é a fonte da verdade para o chat no Windows.

Repo: `https://github.com/joaop-gregorioDS/bankcore-fintech`  
API: `https://bankcore.vortexsoftware.tech` (lab fallback: `http://2.25.126.53`)  
Versão de portfólio: **`version 1.10.25`** (mostrar no login e no perfil/configurações).

---

## Maneira adequada (não negociar no chat)

1. **GitHub é o handoff.** Não copiar prints nem colar o histórico do Mac. No Windows: `git pull origin main` e ler este pacote.
2. **Um chat = um app.** Chat 1: Tauri em `apps/desktop`. Chat 2: Android em `apps/android`. Não misturar.
3. **iOS já existe e é a referência de UX.** Não reinventar telas. Espelhar `apps/ios` + este documento. Contrato HTTP só em `API.md`.
4. **Não WebView da SPA.** `frontend/index.html` é o web banking no browser. Android e iOS são nativos. Tauri é shell nativo + UI Carbon Ledger **própria** (HTML/JS enxuto), cliente HTTP da API — não empacotar a SPA de 2.300 linhas.
5. **Não inventar endpoint. Não copiar marca BB/C6.** Densidade de banco digital; visual = Carbon Ledger.

Ordem no Windows: **Tauri primeiro** (prova a API fora do browser, mais rápido), **depois Android**.

---

## O que já está pronto

| Superfície | Pasta | Estado |
| :--- | :--- | :--- |
| API + ledger | `services/` | VPS, JWT, Pix interno, extrato |
| SPA browser | `frontend/` | Carbon Ledger no Nginx |
| iOS SwiftUI | `apps/ios` | **Feito** — `version 1.10.25`, HTTPS, modo claro padrão |
| Desktop Tauri | `apps/desktop` | **Feito** — `version 1.10.25`, Tauri 2 nativo Windows |
| Android Compose | `apps/android` | A construir no Windows |

Caminho do avaliador (igual nos três): **login Lucas → Pix R$ 1,00 para `12345678900` → extrato (débito Lucas / crédito Maria) → comprovante**. Sem JWT, `POST /accounts/` e `POST /transactions/*` → **401**.

---

## Leitura obrigatória no chat Windows

```
docs/clients/PORTFOLIO.md   ← este arquivo (estratégia + UX)
docs/clients/API.md         ← contrato HTTP (não inventar rota)
docs/clients/DESIGN.md      ← tokens Carbon Ledger
docs/clients/DESKTOP.md     ← só no chat Tauri
docs/clients/ANDROID.md     ← só no chat Android
apps/ios/BankCore/Mock/MockCatalog.swift  ← dados simulados Lucas/Maria
```

Referência visual viva: `apps/ios` (Login, Home, Pix, Extrato, Cartões, Perfil, Hubs).

---

## Consistência visual (obrigatório)

**Modo claro é o padrão** em iOS, Android e Tauri — igual à SPA em https://bankcore.vortexsoftware.tech (`#F4F1EA`). Escuro só se o usuário ligar um controle em Perfil → Configurações (“Modo escuro”). Não seguir o tema do sistema no primeiro launch.

Use a coluna **Claro** no arranque. A coluna Escuro existe para o toggle.

| Papel | Claro (padrão) | Escuro (opcional) |
| :--- | :--- | :--- |
| Fundo | `#F4F1EA` | `#0B0B0C` |
| Painel / header | `#FFFFFF` | `#141416` |
| Card | `#FFFFFF` | `#1C1C1F` |
| Texto | `#121212` | `#F6F1E8` |
| Mudo | `#6B6560` | `#9A958C` |
| Ouro (1 CTA) | `#9A7B32` | `#C4A35A` |
| Débito / Sair | `#B42318` | `#C42B2B` |
| Status | `#2F6B4F` | `#3D7A5A` |
| Linha | `#E4DFD4` | `#2A2A2E` |
| Texto no CTA ouro | `#0B0B0C` sempre | idem |

Regras:

- Ouro **não** pinta a tela inteira. Sem azul BB, sem amarelo BB, sem clone C6.
- Marca: quadrado arredondado ouro + **escudo**. Wordmark `Bank` (texto) + `Core` ouro.
- **Ícone do app (Android launcher / Tauri .ico):** fundo cream `#F4F1EA` + marca ouro `#9A7B32` (mesmo contraste da login web). Referência: `apps/ios/BankCore/Assets.xcassets/AppIcon.appiconset/AppIcon.png`.
- Razão social: **Vortex Software LTDA**. E-mail institucional: `contato@vortexsoftware.tech`.
- Tipografia do sistema (Roboto no Android, Inter ou Plus Jakarta no Tauri). Saldo = único número extra-grande. Valores com tabular nums. `pt-BR`.
- Selo **SIMULADO** (cápsula ouro, 9–10px) em tudo que não grava no ledger.
- Copy do comprovante: “Comprovante BankCore · ledger interno”. Nunca “SPI BACEN” como integração real.
- Rodapé de versão no login e no perfil: `version 1.10.25` (fonte mudo, monoespaçada, tracking aberto).

---

## IA de navegação (o que copiar do BB / iOS)

Copiar **estrutura**, não marca.

**Login**

- Marca geométrica centralizada + wordmark + faixa de portfólio + `version 1.10.25`.
- Cartão do correntista (iniciais) + atalhos Trocar conta / Fazer Pix.
- Dois chips demo: Lucas / Maria.
- Formulário (Acessar / Abrir conta) acessível; não precisa estar aberto o tempo todo.

**Depois do login — abas**

`Início | Pix | Extrato | Cartões | Perfil`

**Início**

- Header: marca + “Olá, {primeiro nome}” + olho (ocultar saldo) + sino (badge).
- Card: **Saldo** (API `balance_reais`, ivory, grande) à esquerda; **Agendado** (soma DDA mock, vermelho, selo Simulado) à direita.
- Grade 2×4: Extrato, Pagar, Pix, Investir, Cartões, Empréstimo, DDA, Ver mais.
- Promo Invest (simulado) + prévia de cartões (limite + carrossel) + chave Pix CPF + últimos lançamentos do **ledger**.

**Pix / Extrato / Comprovante** — ledger real (`API.md`). Pix: CPF só dígitos, lookup `GET /auth/directory/{tax_id}`, confirmação, `idempotency_key` = `pix_<uuid>`. Extrato: DEBIT vermelho, CREDIT texto padrão. Comprovante: papel cream, autenticação `AUT-{IDEMPOTENCY}`, share/PDF local.

**Cartões, Pagar, DDA, Invest, Crédito, Notificações** — mock local (mesmo catálogo do iOS). Toast: “não grava no ledger”.

**Perfil**

- Iniciais, Ag. `0001-9` · Cc. `{account_number}`, visto em, segmento.
- Configurações + Segurança (UX).
- Toggle **Modo escuro** (desligado por padrão; persiste a escolha).
- Bloco **Sobre o app**: `version 1.10.25` + bundle.
- **SAIR DO APP** em vermelho.

---

## Real vs simulado

| Real (grava no ledger) | Simulado (só UX, selo) |
| :--- | :--- |
| Cadastro, login, JWT | Cartões, fatura, limite do cartão |
| Conta corrente e saldo | Agenda DDA, boletos, débitos |
| Pix interno por CPF | Invest, crédito (Tabela Price) |
| Extrato e comprovante | QR Pix, limites Pix, notificações de fatura |

JWT: Keystore / EncryptedPrefs (Android), plugin Tauri de store seguro (não `localStorage` puro). `account_id` só em memória após `POST /accounts/` com `user_id` = `sub` do JWT.

API oficial com HTTPS (`https://bankcore.vortexsoftware.tech`). HTTP claro apenas para o IP da VPS (`2.25.126.53`) em laboratório/debug. Android: cleartext no flavor debug se usar IP direto.

---

## Catálogo mock (Lucas ≠ Maria)

Espelhar `apps/ios/BankCore/Mock/MockCatalog.swift`. Números fixos, não aleatórios a cada abertura.

**Lucas** (`98765432100`) — Carbon Black `•••• 4289`, fatura R$ 2.296,07, limite usado R$ 8.371 / disponível R$ 12.260, DDA AWS+Contabilizei+Vivo+Workspace+Serasa, Invest ~R$ 23.750, crédito R$ 50.000, segmento Vortex Carbon Black Corporate.

**Maria** (`12345678900`) — Carbon Platinum `•••• 8821`, fatura R$ 1.480,30, limite 4.210 / 15.790, DDA condomínio+Unimed+Enel+Claro, Invest menor, crédito R$ 35.000, segmento Vortex Carbon Platinum.

Senha demo: `teste123456`. Agência sempre `0001-9`.

---

## Prompts para colar no Windows

**Chat Tauri** (`apps/desktop`)

> `git pull origin main`. Leia `docs/clients/PORTFOLIO.md`, `DESKTOP.md`, `API.md` e `DESIGN.md`. Espelhe a UX do iOS (`apps/ios`). Scaffold Tauri 2 em `apps/desktop`. Cliente HTTPS de `https://bankcore.vortexsoftware.tech`. v1: login Lucas → Pix → extrato → comprovante. Home viva + simulados + `version 1.10.25`. **Modo claro por padrão**; escuro só no toggle do perfil. Ícone cream `#F4F1EA` + escudo ouro `#9A7B32` (igual à login web). Sem empacotar `frontend/index.html`. Sem inventar endpoint.

**Chat Android** (`apps/android`)

> `git pull origin main`. Leia `docs/clients/PORTFOLIO.md`, `ANDROID.md`, `API.md` e `DESIGN.md`. Espelhe a UX do iOS (`apps/ios`). App Compose em `apps/android`, applicationId `br.vortex.bankcore`. API `https://bankcore.vortexsoftware.tech`. JWT no EncryptedPrefs/Keystore. v1: login Lucas → Pix → extrato → comprovante. Home viva + simulados + `version 1.10.25`. **Modo claro por padrão**; escuro só no toggle do perfil. Launcher cream `#F4F1EA` + escudo ouro `#9A7B32`. Sem WebView da SPA. Sem inventar endpoint.

---

## Pronto quando (cada app)

- Login Lucas, Pix R$ 1,00 para `12345678900`, débito no extrato do Lucas e crédito no da Maria.
- Sem token → o app não chama rota financeira (API 401 se chamar).
- `version 1.10.25` visível no login e no perfil.
- Cartões/DDA/invest com selo Simulado; Pix/extrato sem selo.
- Visual Carbon Ledger **claro por padrão**; ícone cream + ouro como a login web; não um clone de banco de varejo.

## Fora de escopo nestes chats

Alterar o backend, reescrever a SPA, WebView da SPA, iOS (já no Mac).
