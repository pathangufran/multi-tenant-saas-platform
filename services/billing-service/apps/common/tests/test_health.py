import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_health_endpoint_returns_ok():
    client = APIClient()

    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "billing-service",
        "status": "ok",
    }
