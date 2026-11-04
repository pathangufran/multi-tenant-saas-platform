import uuid
import pytest
from django.test import RequestFactory
from apps.tenants.middleware import (
    TenantContextMiddleware,
)
from apps.tenants.models import (
    Tenant,
    TenantMembership,
)

@pytest.mark.django_db
class TestTenantContextMiddleware:

    def setup_method(self):
        self.factory = RequestFactory()

        self.user_id = uuid.uuid4()

        self.tenant = Tenant.objects.create(
            name="Acme Corporation",
            slug="acme",
        )

        TenantMembership.objects.create(
            tenant=self.tenant,
            user_id=self.user_id,
            status=TenantMembership.Status.ACTIVE,
        )

    def test_valid_context_is_attached_to_request(self):
        request = self.factory.get(
            "/test/",
            HTTP_X_TENANT_ID=str(self.tenant.id),
        )

        request.authenticated_user_id = self.user_id

        captured = {}

        def get_response(request):
            captured["context"] = request.tenant_context
            return None

        middleware = TenantContextMiddleware(
            get_response,
        )

        middleware(request)

        context = captured["context"]

        assert context.tenant_id == self.tenant.id
        assert context.user_id == self.user_id

    def test_missing_tenant_header_does_not_require_context(self):
        request = self.factory.get("/test/")

        def get_response(request):
            assert not hasattr(
                request,
                "tenant_context",
            )
            return None

        middleware = TenantContextMiddleware(
            get_response,
        )

        middleware(request)

    def test_missing_authenticated_user_is_rejected(self):
        request = self.factory.get(
            "/test/",
            HTTP_X_TENANT_ID=str(self.tenant.id),
        )

        def get_response(request):
            raise AssertionError(
                "Request should not reach view."
            )

        middleware = TenantContextMiddleware(
            get_response,
        )

        response = middleware(request)

        assert response.status_code == 401

    def test_invalid_tenant_id_is_rejected(self):
        request = self.factory.get(
            "/test/",
            HTTP_X_TENANT_ID="invalid",
        )

        request.authenticated_user_id = self.user_id

        def get_response(request):
            raise AssertionError(
                "Request should not reach view."
            )

        middleware = TenantContextMiddleware(
            get_response,
        )

        response = middleware(request)

        assert response.status_code == 400

    def test_non_member_is_rejected(self):
        request = self.factory.get(
            "/test/",
            HTTP_X_TENANT_ID=str(self.tenant.id),
        )

        request.authenticated_user_id = uuid.uuid4()

        def get_response(request):
            raise AssertionError(
                "Request should not reach view."
            )

        middleware = TenantContextMiddleware(
            get_response,
        )

        response = middleware(request)

        assert response.status_code == 403