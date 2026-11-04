import uuid
import pytest
from rest_framework.test import APIClient
from apps.tenants.models import (
    Tenant,TenantMembership
)

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def authenticated_client(monkeypatch, api_client):
    user_id = uuid.uuid4()

    class MockUser:
        id = user_id
        is_authenticated = True

    api_client.force_authenticate(
        user=MockUser()
    )

    original_request = api_client.request

    def request(**kwargs):
        request = original_request(**kwargs)
        request.authenticated_user_id = user_id
        return request

    monkeypatch.setattr(
        api_client,
        "request",
        request,
    )

    return api_client, user_id

@pytest.fixture
def tenant_with_membership(authenticated_client):
    client, user_id = authenticated_client

    tenant = Tenant.objects.create(
        name="Test Tenant",
        slug="test-tenant",
    )

    TenantMembership.objects.create(
        tenant=tenant,
        user_id=user_id,
        status=TenantMembership.Status.ACTIVE,
    )

    return client, user_id, tenant

@pytest.mark.django_db
class TestTenantUpdateAPI:

    def test_update_tenant_name(
        self,
        tenant_with_membership,
    ):
        client, user_id, tenant = (
            tenant_with_membership
        )

        response = client.patch(
            f"/api/v1/tenants/{tenant.id}/",
            {
                "name": "Updated Tenant",
            },
            format="json",
        )

        assert response.status_code == 200

        tenant.refresh_from_db()

        assert tenant.name == "Updated Tenant"
        assert tenant.slug == "test-tenant"

    def test_update_tenant_slug(
        self,
        tenant_with_membership,
    ):
        client, user_id, tenant = (
            tenant_with_membership
        )

        response = client.patch(
            f"/api/v1/tenants/{tenant.id}/",
            {
                "slug": "updated-tenant",
            },
            format="json",
        )

        assert response.status_code == 200

        tenant.refresh_from_db()

        assert tenant.slug == "updated-tenant"

    def test_update_tenant_name_and_slug(
        self,
        tenant_with_membership,
    ):
        client, user_id, tenant = (
            tenant_with_membership
        )

        response = client.patch(
            f"/api/v1/tenants/{tenant.id}/",
            {
                "name": "Updated Company",
                "slug": "updated-company",
            },
            format="json",
        )

        assert response.status_code == 200

        tenant.refresh_from_db()

        assert tenant.name == "Updated Company"
        assert tenant.slug == "updated-company"

    def test_empty_name_rejected(
        self,
        tenant_with_membership,
    ):
        client, user_id, tenant = (
            tenant_with_membership
        )

        response = client.patch(
            f"/api/v1/tenants/{tenant.id}/",
            {
                "name": "",
            },
            format="json",
        )

        assert response.status_code == 400

        tenant.refresh_from_db()

        assert tenant.name == "Test Tenant"

    def test_empty_slug_rejected(
        self,
        tenant_with_membership,
    ):
        client, user_id, tenant = (
            tenant_with_membership
        )

        response = client.patch(
            f"/api/v1/tenants/{tenant.id}/",
            {
                "slug": "",
            },
            format="json",
        )

        assert response.status_code == 400

        tenant.refresh_from_db()

        assert tenant.slug == "test-tenant"

    def test_duplicate_slug_rejected(
        self,
        tenant_with_membership,
    ):
        client, user_id, tenant = (
            tenant_with_membership
        )

        Tenant.objects.create(
            name="Another Tenant",
            slug="another-tenant",
        )

        response = client.patch(
            f"/api/v1/tenants/{tenant.id}/",
            {
                "slug": "another-tenant",
            },
            format="json",
        )

        assert response.status_code == 400

        tenant.refresh_from_db()

        assert tenant.slug == "test-tenant"

    def test_user_cannot_update_other_users_tenant(
        self,
        authenticated_client,
    ):
        client, user_id = authenticated_client

        other_user_id = uuid.uuid4()

        tenant = Tenant.objects.create(
            name="Private Tenant",
            slug="private-tenant",
        )

        TenantMembership.objects.create(
            tenant=tenant,
            user_id=other_user_id,
            status=TenantMembership.Status.ACTIVE,
        )

        response = client.patch(
            f"/api/v1/tenants/{tenant.id}/",
            {
                "name": "Hacked Tenant",
            },
            format="json",
        )

        assert response.status_code == 404

        tenant.refresh_from_db()

        assert tenant.name == "Private Tenant"

@pytest.mark.django_db
class TestTenantLifecycleAPI:

    def test_suspend_tenant(
        self,
        tenant_with_membership,
    ):
        client, user_id, tenant = (
            tenant_with_membership
        )

        response = client.post(
            f"/api/v1/tenants/{tenant.id}/suspend/"
        )

        assert response.status_code == 200

        tenant.refresh_from_db()

        assert tenant.status == Tenant.Status.SUSPENDED

    def test_deactivate_tenant(
        self,
        tenant_with_membership,
    ):
        client, user_id, tenant = (
            tenant_with_membership
        )

        response = client.post(
            f"/api/v1/tenants/{tenant.id}/deactivate/"
        )

        assert response.status_code == 200

        tenant.refresh_from_db()

        assert (
            tenant.status
            == Tenant.Status.DEACTIVATED
        )

    def test_activate_tenant(
        self,
        tenant_with_membership,
    ):
        client, user_id, tenant = (
            tenant_with_membership
        )

        tenant.status = Tenant.Status.SUSPENDED
        tenant.save(
            update_fields=["status"]
        )

        response = client.post(
            f"/api/v1/tenants/{tenant.id}/activate/"
        )

        assert response.status_code == 200

        tenant.refresh_from_db()

        assert tenant.status == Tenant.Status.ACTIVE

    def test_suspended_membership_cannot_suspend_tenant(
        self,
        authenticated_client,
    ):
        client, user_id = authenticated_client

        tenant = Tenant.objects.create(
            name="Tenant",
            slug="tenant",
        )

        TenantMembership.objects.create(
            tenant=tenant,
            user_id=user_id,
            status=TenantMembership.Status.SUSPENDED,
        )

        response = client.post(
            f"/api/v1/tenants/{tenant.id}/suspend/"
        )

        assert response.status_code == 404

        tenant.refresh_from_db()

        assert tenant.status == Tenant.Status.ACTIVE

    def test_removed_membership_cannot_update_tenant(
        self,
        authenticated_client,
    ):
        client, user_id = authenticated_client

        tenant = Tenant.objects.create(
            name="Tenant",
            slug="tenant",
        )

        TenantMembership.objects.create(
            tenant=tenant,
            user_id=user_id,
            status=TenantMembership.Status.REMOVED,
        )

        response = client.patch(
            f"/api/v1/tenants/{tenant.id}/",
            {
                "name": "Changed",
            },
            format="json",
        )

        assert response.status_code == 404

        tenant.refresh_from_db()

        assert tenant.name == "Tenant"

    def test_nonexistent_tenant_cannot_be_updated(
        self,
        authenticated_client,
    ):
        client, user_id = authenticated_client

        tenant_id = uuid.uuid4()

        response = client.patch(
            f"/api/v1/tenants/{tenant_id}/",
            {
                "name": "Updated",
            },
            format="json",
        )

        assert response.status_code == 404

    def test_nonexistent_tenant_cannot_be_suspended(
        self,
        authenticated_client,
    ):
        client, user_id = authenticated_client

        tenant_id = uuid.uuid4()

        response = client.post(
            f"/api/v1/tenants/{tenant_id}/suspend/"
        )

        assert response.status_code == 404