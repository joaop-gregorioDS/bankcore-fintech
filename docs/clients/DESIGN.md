# Design — Carbon Ledger (clientes)

Não copiar marca C6. Copiar a **densidade** de um banco digital: tabs, saldo grande, um CTA, extrato com débito em vermelho.

## Tokens

| Papel | Escuro | Claro |
| :--- | :--- | :--- |
| Fundo | `#0B0B0C` | `#F4F1EA` |
| Painel / card | `#1C1C1F` | `#FFFFFF` |
| Texto | `#F6F1E8` | `#121212` |
| Mudo | `#9A958C` | `#6B6560` |
| Ouro (acento, 1 CTA) | `#C4A35A` | `#9A7B32` |
| Saída / débito | `#C42B2B` | `#B42318` |
| Entrada | mesmo do texto + prefixo `+` | idem |
| Status (conta ativa) | `#3D7A5A` | `#2F6B4F` |
| Linha | `#2A2A2E` | `#E4DFD4` |

Ouro **não** pinta a tela inteira. Vermelho **só** em dinheiro saindo e “Sair”.

## Tipografia

- UI: SF Pro (iOS), Roboto/Sans (Android), Plus Jakarta ou Inter (Tauri).
- Saldo: o único número extra-grande.
- Valores: tabular nums.

## Telas v1

1. **Login** — CPF, senha, atalho João / Maria, faixa “demonstração”.
2. **Início** — saldo, limite (pode ser mock), CTA ouro “Pix”, atalho extrato.
3. **Pix** — CPF destino, valor, descrição, confirmar.
4. **Extrato** — lista; débito vermelho; tap abre comprovante.
5. **Comprovante** — titular, valor, tipo, data, autenticação, rodapé “ledger interno, não é SPI/BACEN”. Share sheet / print.

Tema claro e escuro se der tempo; escuro primeiro no iOS/Android (banco digital), claro já é o da SPA.

## Copy

- “Comprovante BankCore · ledger interno”
- Nunca “SPI BACEN” como se fosse integração real.
