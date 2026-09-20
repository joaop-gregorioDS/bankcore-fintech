SELECT 'CREATE DATABASE bankcore_audit'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'bankcore_audit')\gexec
