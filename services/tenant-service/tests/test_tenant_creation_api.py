import uuid
import pytest
from rest_framework.test import APIClient
from apps.tenants.models import (
    Tenant,
    TenantMembership,
)

class AuthenticatedUser:
    def __init__(self, user_id):
        self.id = user_id
        self.is_authenticated = True

@pytest.mark.django_db
class TestTenantCreationAPI:

    def test_create_tenant(self):
        user_id = uuid.uuid4()

        client = APIClient()

        client.force_authenticate(
            user=AuthenticatedUser(user_id)
        )

        response = client.post(
            "/api/v1/tenants/",
            {
                "name": "Acme Corporation",
                "slug": "acme-corporation",
            },
            format="json",
        )

        assert response.status_code == 201

        tenant = Tenant.objects.get(
            slug="acme-corporation"
        )

        assert tenant.name == "Acme Corporation"

        membership = TenantMembership.objects.get(
            tenant=tenant,
            user_id=user_id,
        )

        assert membership.status == TenantMembership.Status.ACTIVE

    def test_duplicate_slug_rejected(self):
        Tenant.objects.create(
            name="Existing Tenant",
            slug="existing-tenant",
        )

        user_id = uuid.uuid4()

        client = APIClient()

        client.force_authenticate(
            user=AuthenticatedUser(user_id)
        )

        response = client.post(
            "/api/v1/tenants/",
            {
                "name": "Another Tenant",
                "slug": "existing-tenant",
            },
            format="json",
        )

        assert response.status_code == 400

    def test_invalid_payload_rejected(self):
        user_id = uuid.uuid4()

        client = APIClient()

        client.force_authenticate(
            user=AuthenticatedUser(user_id)
        )

        response = client.post(
            "/api/v1/tenants/",
            {
                "name": "",
                "slug": "",
            },
            format="json",
        )

        assert response.status_code == 400