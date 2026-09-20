import pytest
from django.urls import reverse
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_openapi_schema_is_available():
    client = APIClient()

    response = client.get(
        reverse("schema")
    )

    assert response.status_code == 200

    assert "openapi" in response.data
    assert response.data["info"]["title"] == (
        "SaaS Platform Tenant Service API"
    )

@pytest.mark.django_db
def test_swagger_ui_is_available():
    client = APIClient()

    response = client.get(
        reverse("swagger-ui")
    )

    assert response.status_code == 200