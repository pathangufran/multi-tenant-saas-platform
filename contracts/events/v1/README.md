# SaaS Platform Event Contract v1

## Kafka topic

saas.events.v1

## Dead-letter topic

saas.events.dlq.v1

## Partition key

Tenant-owned events:

{tenant_id}:{aggregate_type}:{aggregate_id}

Platform events:

{aggregate_type}:{aggregate_id}

## Delivery semantics

The application assumes at-least-once event delivery.

Consumers must implement idempotent processing using event_id.

Do not assume exactly-once business processing merely because
Kafka producer transactions are enabled.

## Ordering

Kafka preserves ordering within a partition.

Events belonging to the same aggregate should use the same
partition key.

## Event ownership

Each service publishes events only for its own domain.

## Event metadata

Every event follows event.schema.json.

## Versioning

v1 envelope changes must remain backward compatible.

Breaking envelope changes require a new contract version.

Breaking event payload changes require an explicitly versioned
event contract.

## Security

- Never publish passwords or authentication tokens.
- Never publish payment card details.
- Do not expose internal secrets.
- Minimize personally identifiable information.
- Validate tenant context at the producer and consumer boundaries.

## Schema validation

Run:

python -m unittest discover -s tests -v
