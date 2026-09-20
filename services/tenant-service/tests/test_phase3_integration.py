import uuid
import pytest
from rest_framework.test import APIClient
from apps.tenants.context_service import (
    TenantContextService,
)
from apps.tenants.services import TenantService
from apps.tenants.models import (
    Tenant,TenantMembership,AuditEvent
)

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def authenticated_client(
    monkeypatch,
    api_client,
):
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

@pytest.mark.django_db
class TestPhase3Integration:

    def test_complete_tenant_lifecycle(
        self,
        authenticated_client,
    ):
        client, user_id = authenticated_client

        # -------------------------------------------------
        # 1. Create tenant
        # -------------------------------------------------

        response = client.post(
            "/api/v1/tenants/",
            {
                "name": "Acme Corporation",
                "slug": "acme",
            },
            format="json",
        )

        assert response.status_code == 201

        tenant_id = response.data["id"]

        tenant = Tenant.objects.get(
            id=tenant_id
        )

        assert tenant.name == "Acme Corporation"
        assert tenant.slug == "acme"
        assert tenant.status == Tenant.Status.ACTIVE

        # -------------------------------------------------
        # 2. Owner membership exists
        # -------------------------------------------------

        membership = (
            TenantMembership.objects.get(
                tenant=tenant,
                user_id=user_id,
            )
        )

        assert (
            membership.status
            == TenantMembership.Status.ACTIVE
        )

        # -------------------------------------------------
        # 3. Tenant context can be resolved
        # -------------------------------------------------

        context = TenantContextService.resolve(
            tenant_id=tenant.id,
            user_id=user_id,
        )

        assert context.tenant_id == tenant.id
        assert context.user_id == user_id

        # -------------------------------------------------
        # 4. Tenant appears in user's list
        # -------------------------------------------------

        response = client.get(
            "/api/v1/tenants/list/"
        )

        assert response.status_code == 200
        assert len(response.data) == 1
        assert response.data[0]["id"] == str(
            tenant.id
        )

        # -------------------------------------------------
        # 5. Retrieve tenant
        # -------------------------------------------------

        response = client.get(
            f"/api/v1/tenants/{tenant.id}/"
        )

        assert response.status_code == 200
        assert response.data["id"] == str(
            tenant.id
        )

        # -------------------------------------------------
        # 6. Update tenant
        # -------------------------------------------------

        response = client.patch(
            f"/api/v1/tenants/{tenant.id}/",
            {
                "name": "Acme Technologies",
                "slug": "acme-tech",
            },
            format="json",
        )

        assert response.status_code == 200

        tenant.refresh_from_db()

        assert tenant.name == "Acme Technologies"
        assert tenant.slug == "acme-tech"

        # -------------------------------------------------
        # 7. Audit update
        # -------------------------------------------------

        assert AuditEvent.objects.filter(
            tenant_id=tenant.id,
            actor_user_id=user_id,
            event_type=(
                AuditEvent.EventType.TENANT_UPDATED
            ),
        ).exists()

        # -------------------------------------------------
        # 8. Suspend tenant
        # -------------------------------------------------

        response = client.post(
            f"/api/v1/tenants/{tenant.id}/suspend/"
        )

        assert response.status_code == 200

        tenant.refresh_from_db()

        assert (
            tenant.status
            == Tenant.Status.SUSPENDED
        )

        # -------------------------------------------------
        # 9. Suspended tenant cannot establish context
        # -------------------------------------------------

        with pytest.raises(Exception):
            TenantContextService.resolve(
                tenant_id=tenant.id,
                user_id=user_id,
            )

        # -------------------------------------------------
        # 10. Activate tenant
        # -------------------------------------------------

        response = client.post(
            f"/api/v1/tenants/{tenant.id}/activate/"
        )

        assert response.status_code == 200

        tenant.refresh_from_db()

        assert (
            tenant.status
            == Tenant.Status.ACTIVE
        )

        # -------------------------------------------------
        # 11. Context works again
        # -------------------------------------------------

        context = TenantContextService.resolve(
            tenant_id=tenant.id,
            user_id=user_id,
        )

        assert context.tenant_id == tenant.id

        # -------------------------------------------------
        # 12. Deactivate tenant
        # -------------------------------------------------

        response = client.post(
            f"/api/v1/tenants/{tenant.id}/deactivate/"
        )

        assert response.status_code == 200

        tenant.refresh_from_db()

        assert (
            tenant.status
            == Tenant.Status.DEACTIVATED
        )

        # -------------------------------------------------
        # 13. Audit events exist
        # -------------------------------------------------

        event_types = set(
            AuditEvent.objects
            .filter(
                tenant_id=tenant.id
            )
            .values_list(
                "event_type",
                flat=True,
            )
        )

        assert (
            AuditEvent.EventType.TENANT_CREATED
            in event_types
        )

        assert (
            AuditEvent.EventType.TENANT_UPDATED
            in event_types
        )

        assert (
            AuditEvent.EventType.TENANT_SUSPENDED
            in event_types
        )

        assert (
            AuditEvent.EventType.TENANT_ACTIVATED
            in event_types
        )

        assert (
            AuditEvent.EventType.TENANT_DEACTIVATED
            in event_types
        )