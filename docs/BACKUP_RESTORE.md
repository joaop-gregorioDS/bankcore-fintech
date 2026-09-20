# Backup and restore local

O P1-D usa `pg_dump` e `pg_restore` em containers PostgreSQL descartáveis. O
host precisa apenas do Docker; não é necessário instalar ferramentas PostgreSQL
localmente.

```powershell
.\scripts\backup-restore.ps1
```

O comando cria dois PostgreSQL temporários, aplica migrations somente no banco
fonte, sem iniciar Auth, Transactions, Redis, Nginx ou a VPS, e então cria
dumps separados de Auth e Transactions, gera manifest com tamanho e SHA-256,
restaura em bancos vazios e compara `alembic_version`, contagens, saldos,
ledger, idempotência e integridade referencial. Também valida uma credencial
sintética, rejeita dump adulterado e rejeita alvos fora de `bankcore_test_`.

Os containers, volumes e artefatos são removidos ao terminar. Com
`-KeepArtifacts`, os dumps ficam somente no diretório local indicado para
inspeção controlada; não devem ser enviados ao Git.

Redis não é fonte da verdade financeira. A fonte autoritativa é o PostgreSQL,
especialmente `accounts`, `ledger_transactions` e `ledger_entries`. Por isso o
P1-D não faz dump nem restore de Redis.
