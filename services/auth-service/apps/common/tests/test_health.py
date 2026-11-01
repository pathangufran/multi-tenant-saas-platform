import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_health_check(client):
    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
    }

@pytest.mark.django_db
def test_readiness_check(client):
    response = client.get("/ready/")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ready"
    assert data["checks"]["database"] == "ok"
    assert data["checks"]["redis"] == "ok"