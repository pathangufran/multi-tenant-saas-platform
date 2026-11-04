# SaaS Platform - Workload Profile

## Target
500 concurrent virtual users.

## Ramp-up
5-10 minutes.

## Sustained load
15 minutes.

## Ramp-down
5 minutes.

## Workload distribution

| Service | Traffic Share |
|---|---:|
| Auth | 15% |
| Tenant | 10% |
| Core | 45% |
| Billing | 10% |
| Notification | 20% |

## User journeys

### Authentication
1. Login.
2. Refresh access token.
3. Access protected endpoint.

### Tenant
1. List user tenants.
2. Fetch current tenant.
3. Fetch tenant membership.

### Core
1. List projects.
2. Fetch project details.
3. List tasks.
4. Create task.
5. Update task status.
6. List comments.
7. List teams.

### Billing
1. List available plans.
2. Fetch tenant subscription.
3. List invoices.

### Notification
1. List notifications.
2. Fetch unread count.
3. Mark notification as read.

## Initial performance targets

| Metric | Target |
|---|---:|
| Read API p95 | < 300 ms |
| Write API p95 | < 500 ms |
| Error rate | < 1% |
| Background task success | >= 99% |

## Test conditions

- Use a dedicated local test environment.
- Use seeded test accounts and tenant data.
- Do not run destructive tests against real customer data.
- Record application, database, Redis, and Celery metrics.
- Record the machine specifications.
- Repeat tests with the same dataset and configuration.
