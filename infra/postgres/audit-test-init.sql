SELECT 'CREATE DATABASE bankcore_test_transactions'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'bankcore_test_transactions')\gexec

SELECT 'CREATE DATABASE bankcore_test_audit'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'bankcore_test_audit')\gexec
