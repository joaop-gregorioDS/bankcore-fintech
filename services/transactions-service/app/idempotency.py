import hashlib
import json
from uuid import UUID, uuid5

TRANSACTION_NAMESPACE = UUID("9f5a7b35-1f73-4b3f-9e84-3df1d39f4d88")


def build_request_fingerprint(
    *,
    user_id: UUID,
    account_id: UUID,
    operation_type: str,
    idempotency_key: str,
    amount_cents: int,
    destination_account_id: UUID | None = None,
    description: str | None = None,
) -> str:
    payload = {
        "account_id": str(account_id),
        "amount_cents": amount_cents,
        "description": description,
        "destination_account_id": str(destination_account_id) if destination_account_id else None,
        "idempotency_key": idempotency_key,
        "operation_type": operation_type,
        "user_id": str(user_id),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_transaction_id(
    *,
    user_id: UUID,
    account_id: UUID,
    operation_type: str,
    idempotency_key: str,
) -> UUID:
    scope = "|".join((str(user_id), str(account_id), operation_type, idempotency_key))
    return uuid5(TRANSACTION_NAMESPACE, scope)
