-- The test runner uses two explicitly test-named databases.
SELECT 'CREATE DATABASE bankcore_test_transactions'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'bankcore_test_transactions')\gexec
