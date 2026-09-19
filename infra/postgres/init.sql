-- bankcore_auth is created by POSTGRES_DB. Create only the additional
-- service databases, and keep this script safe if initialization is retried.
SELECT 'CREATE DATABASE bankcore_accounts'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'bankcore_accounts')\gexec

SELECT 'CREATE DATABASE bankcore_transactions'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'bankcore_transactions')\gexec
