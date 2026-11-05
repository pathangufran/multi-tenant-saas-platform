# SaaS Platform Load Testing

## Install

python -m venv .venv

Windows:
.venv\Scripts\Activate.ps1

pip install -r requirements.txt

## Configure

Copy .env.example to .env.

Configure:
- Auth URL and login route
- Test credentials
- Service URLs
- Actual API endpoint paths
- Valid write payloads

## Run Locust UI

locust -f locustfile.py

Open:
http://localhost:8089

## Headless tests

50 users:

locust -f locustfile.py --headless -u 50 -r 5 -t 5m --csv reports/50-users --html reports/50-users.html

100 users:

locust -f locustfile.py --headless -u 100 -r 10 -t 10m --csv reports/100-users --html reports/100-users.html

250 users:

locust -f locustfile.py --headless -u 250 -r 10 -t 15m --csv reports/250-users --html reports/250-users.html

500 users:

locust -f locustfile.py --headless -u 500 -r 10 -t 15m --csv reports/500-users --html reports/500-users.html

## Important

Do not increase concurrency until the previous test has been
reviewed.

Record:
- Requests per second
- p50, p95, p99 response time
- Failure count and failure percentage
- CPU and memory
- PostgreSQL connections
- Redis metrics
- Celery queue depth
