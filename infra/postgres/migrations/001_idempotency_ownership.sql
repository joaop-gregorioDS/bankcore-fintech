BEGIN;

ALTER TABLE ledger_transactions
    DROP CONSTRAINT IF EXISTS ledger_transactions_idempotency_key_key;

CREATE INDEX IF NOT EXISTS idx_ledger_idempotency_key
    ON ledger_transactions (idempotency_key);

CREATE TABLE IF NOT EXISTS idempotency_records (
    id UUID PRIMARY KEY,
    idempotency_key VARCHAR(100) NOT NULL,
    user_id UUID NOT NULL,
    account_id UUID NOT NULL,
    operation_type VARCHAR(20) NOT NULL,
    request_fingerprint VARCHAR(64) NOT NULL,
    transaction_id UUID NULL REFERENCES ledger_transactions(id),
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_idempotency_scope
    ON idempotency_records (user_id, account_id, operation_type, idempotency_key);

CREATE INDEX IF NOT EXISTS idx_idempotency_transaction
    ON idempotency_records (transaction_id);

COMMIT;
