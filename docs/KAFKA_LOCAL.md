# Kafka KRaft local smoke test

This is the isolated P3-B Kafka infrastructure test. It is intentionally not part of the main BankCore Compose environment and does not connect to Transactions, PostgreSQL, Redis or the Risk Service.

## Topology

- `apache/kafka:3.9.0` in single-node combined broker/controller KRaft mode;
- no ZooKeeper;
- internal Docker listener at `kafka:9092`;
- no host port published;
- a temporary named volume mounted on the image's writable Kafka data directory for KRaft metadata and log persistence during the test;
- topic `bankcore.transaction.completed.v1` with one partition and replication factor one.

The advertised listener uses the Docker service name, so clients inside the network do not depend on host-specific addresses. The Compose network is internal and the runner executes the Kafka CLI inside the broker container.

## Run

Windows PowerShell:

```powershell
./scripts/kafka-test.ps1
```

Linux/macOS:

```bash
./scripts/kafka-test.sh
```

The runner validates the Compose file, starts and waits for the broker healthcheck, creates and describes the topic, produces and consumes a synthetic event, restarts the broker, verifies the topic again, repeats produce/consume, and removes the container, network and volume even after failure.

The event is synthetic and contains only an `event_id`, `event_type` and `event_version`. No BankCore data, credentials or production configuration is used.

## Deliberate scope boundary

This stage does not implement the transactional outbox, a publisher, real consumers, retry/DLQ, Schema Registry or CI integration. Those belong to later P3 phases after the broker infrastructure is proven.
