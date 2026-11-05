# SaaS Platform Event Catalogue — v1

## Auth Service

| Event Type | Aggregate |
|---|---|
| user.registered | user |
| user.email_verified | user |

## Tenant Service

| Event Type | Aggregate |
|---|---|
| tenant.created | tenant |
| member.invited | membership |
| member.joined | membership |

## Core Service

| Event Type | Aggregate |
|---|---|
| project.created | project |
| task.created | task |
| task.assigned | task |
| task.completed | task |

## Billing Service

| Event Type | Aggregate |
|---|---|
| subscription.created | subscription |
| subscription.activated | subscription |
| payment.succeeded | payment |
| payment.failed | payment |
| invoice.generated | invoice |

## Notification Service

| Event Type | Aggregate |
|---|---|
| notification.sent | notification |

## Naming convention

<domain>.<action>

Examples:
- task.assigned
- tenant.created
- payment.succeeded

Event names describe something that has already happened.

Use past-tense domain events rather than commands.

Good:
- task.assigned
- invoice.generated

Avoid:
- assign.task
- generate.invoice

## Rules

1. Event names are lowercase.
2. Event names are immutable after publication.
3. Breaking payload changes require a new schema version.
4. Producers own their event definitions.
5. Consumers must tolerate unknown optional fields.
6. Consumers must reject unsupported major schema versions.
7. Events must never contain passwords, JWTs, access tokens,
   card numbers, CVVs, or secret keys.
8. Avoid unnecessary personal information.
9. Use identifiers rather than copying entire database records.
