# Investimentos Pro

**Simulador desktop de daytrade e análise técnica do ecossistema BankCore.**

Gráficos, indicadores, boletas e estratégias automatizadas em uma interface alinhada à identidade visual BankCore, para estudo e prática em conta demo.

| Distribuição | Detalhes |
| --- | --- |
| Versão | 4.0.25 |
| Plataforma | Windows 10/11 x64 |
| Modalidade | Simulação educacional |
| Conteúdo público | Executável e documentação |

## Arquitetura e tecnologia

O Investimentos Pro é um aplicativo desktop construído com **Tauri 2**, combinando um núcleo nativo em **Rust** com uma interface em **React, TypeScript e Vite**. Essa arquitetura mantém a experiência de uma aplicação web moderna em um executável leve para Windows, sem exigir Node.js ou Rust no computador do usuário.

> Não conecta corretoras nem movimenta dinheiro real. Esta versão opera localmente e não compartilha autenticação, contas ou saldo com o backend bancário do BankCore.

## Download e instalação

Os artefatos de distribuição estão neste módulo e podem ser publicados em [Releases do BankCore](https://github.com/joaop-gregorioDS/bankcore-fintech/releases), usando a tag sugerida `investimentos-pro-v4.0.25`.

1. Baixe `Investimentos-Pro-4.0.25-windows-x64.zip` e extraia seu conteúdo.
2. Verifique se o Microsoft Edge WebView2 Runtime está instalado.
3. Execute `Investimentos-Pro-4.0.25-windows-x64.exe`.
4. Entre como convidado ou utilize o cadastro local.
5. Selecione um ativo e pratique com a conta demo.

Também é possível baixar somente o executável. Não é necessário instalar Node.js ou Rust. Os arquivos de distribuição ficam na pasta `release/` deste módulo e também podem ser anexados a uma release do GitHub.

## Recursos

- Gráficos de candles: 1m, 5m, 15m, 1H e 1D.
- Indicadores técnicos e escalas independentes para osciladores.
- Chart Trading configurável: compra verde, venda vermelha e ações azuis.
- Boletas de compra e venda com revisão de preço e quantidade antes do envio.
- Menu contextual para boletas, exibir/ocultar Chart Trading, inserir indicador e selecionar período.
- Acompanhamento de posições, ordens pendentes e resultados simulados.
- Editor de estratégias Algo Trading em Rhai.
- Interface BankCore com superfícies translúcidas e botão Sair na barra lateral inferior.

## Dados locais

Banco SQLite, sessão, preferências e logs são armazenados em:

```text
%APPDATA%\com.investimentos.pro\
```

A execução direta dispensa instalar o aplicativo, mas não mantém os dados junto ao executável. Copiar o `.exe` não transfere contas ou histórico. Para backup, feche o aplicativo e copie a pasta de dados. Essa pasta não deve ser incluída na publicação.

## Organização no monorepositório

Local sugerido para esta documentação: `apps/investimentos-pro/`, no [repositório BankCore](https://github.com/joaop-gregorioDS/bankcore-fintech).

```text
apps/investimentos-pro/
├── README.md
├── LICENSE
└── RELEASE_NOTES.md
```

Distribua o executável, o ZIP e `SHA256SUMS.txt` como anexos da release. O pacote não inclui código-fonte. A tag `investimentos-pro-v4.0.25` distingue este aplicativo das versões do BankCore.

## Integridade do download

Compare o resultado abaixo com a entrada correspondente de `SHA256SUMS.txt`:

```powershell
Get-FileHash .\Investimentos-Pro-4.0.25-windows-x64.exe -Algorithm SHA256
```

## Suporte

Abra uma [Issue](https://github.com/joaop-gregorioDS/bankcore-fintech/issues) identificando o módulo Investimentos Pro, a versão do Windows e os passos para reproduzir. Remova dados pessoais de capturas e logs antes de compartilhá-los.

## Licença e finalidade

Consulte `LICENSE`, incluída na distribuição. Ferramenta educacional: resultados simulados não garantem resultados futuros e não constituem recomendação de investimento.
