import pytest
from django.urls import reverse
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_openapi_schema_contains_rbac_paths():
    client = APIClient()

    response = client.get(
        reverse("schema"),
    )

    assert response.status_code == 200

    schema = response.json()

    paths = schema["paths"]

    assert "/api/v1/tenants/roles/" in paths

    assert (
        "/api/v1/tenants/roles/{role_id}/"
        in paths
    )

    assert (
        "/api/v1/tenants/memberships/"
        "{membership_id}/role/"
        in paths
    )

    assert (
        "/api/v1/tenants/object-permissions/users/"
        in paths
    )

    assert (
        "/api/v1/tenants/object-permissions/roles/"
        in paths
    )