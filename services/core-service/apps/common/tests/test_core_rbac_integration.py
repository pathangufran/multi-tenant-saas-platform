import os
import pytest
from uuid import uuid4
from types import SimpleNamespace
from unittest.mock import Mock, patch
from rest_framework.test import APIRequestFactory
from apps.common.rbac import TenantServiceRBACPermission

@pytest.mark.django_db
class TestTenantServiceRBACPermission:
    def setup_method(self):
        self.factory = APIRequestFactory()
        self.permission = TenantServiceRBACPermission()

        self.user_id = uuid4()
        self.tenant_id = uuid4()

        self.view = SimpleNamespace(
            required_permission="projects.read",
        )

    def _build_request(self):
        request = self.factory.get("/api/v1/projects/")

        request.user = SimpleNamespace(
            is_authenticated=True,
        )

        request.authenticated_user_id = self.user_id
        request.tenant_context = SimpleNamespace(
            tenant_id=self.tenant_id,
        )

        return request

    @patch("apps.common.rbac.requests.post")
    def test_allows_request_when_tenant_service_allows_permission(
        self,
        mock_post,
    ):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "allowed": True,
        }

        mock_post.return_value = mock_response

        request = self._build_request()

        result = self.permission.has_permission(
            request,
            self.view,
        )

        assert result

        mock_post.assert_called_once()

        call_kwargs = mock_post.call_args.kwargs

        assert call_kwargs["json"] == {
            "user_id": str(self.user_id),
            "tenant_id": str(self.tenant_id),
            "permission_code": "projects.read",
        }

    @patch("apps.common.rbac.requests.post")
    def test_denies_request_when_tenant_service_denies_permission(
        self,
        mock_post,
    ):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "allowed": False,
        }

        mock_post.return_value = mock_response

        request = self._build_request()

        result = self.permission.has_permission(
            request,
            self.view,
        )

        assert result is False

    @patch("apps.common.rbac.requests.post")
    def test_fails_closed_when_tenant_service_is_unavailable(
        self,
        mock_post,
    ):
        import requests

        mock_post.side_effect = requests.RequestException(
            "Tenant service unavailable"
        )

        request = self._build_request()

        result = self.permission.has_permission(
            request,
            self.view,
        )

        assert result is False

    @patch("apps.common.rbac.requests.post")
    def test_denies_when_tenant_service_returns_non_200(
        self,
        mock_post,
    ):
        mock_response = Mock()
        mock_response.status_code = 403

        mock_post.return_value = mock_response

        request = self._build_request()

        result = self.permission.has_permission(
            request,
            self.view,
        )

        assert result is False

    @patch("apps.common.rbac.requests.post")
    def test_denies_when_response_is_invalid_json(
        self,
        mock_post,
    ):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError(
            "Invalid JSON"
        )

        mock_post.return_value = mock_response

        request = self._build_request()

        result = self.permission.has_permission(
            request,
            self.view,
        )

        assert result is False

    @patch("apps.common.rbac.requests.post")
    def test_denies_when_tenant_context_is_missing(
        self,
        mock_post,
    ):
        request = self._build_request()
        request.tenant_context = None

        result = self.permission.has_permission(
            request,
            self.view,
        )

        assert result is False
        mock_post.assert_not_called()

    @patch("apps.common.rbac.requests.post")
    def test_denies_when_authenticated_user_is_missing(
        self,
        mock_post,
    ):
        request = self._build_request()
        request.authenticated_user_id = None

        result = self.permission.has_permission(
            request,
            self.view,
        )

        assert result is False
        mock_post.assert_not_called()

    @patch("apps.common.rbac.requests.post")
    def test_denies_when_required_permission_is_missing(
        self,
        mock_post,
    ):
        request = self._build_request()

        view = SimpleNamespace(
            required_permission=None,
        )

        result = self.permission.has_permission(
            request,
            view,
        )

        assert result is False
        mock_post.assert_not_called()

    @patch("apps.common.rbac.requests.post")
    def test_denies_when_rbac_url_is_missing(
        self,
        mock_post,
        monkeypatch,
    ):
        monkeypatch.delenv(
            "TENANT_SERVICE_RBAC_CHECK_URL",
            raising=False,
        )

        monkeypatch.setenv(
            "TENANT_SERVICE_INTERNAL_SERVICE_KEY",
            "test-secret",
        )

        request = self._build_request()

        result = self.permission.has_permission(
            request,
            self.view,
        )

        assert result is False
        mock_post.assert_not_called()

    @patch("apps.common.rbac.requests.post")
    def test_denies_when_internal_service_key_is_missing(
        self,
        mock_post,
        monkeypatch,
    ):
        monkeypatch.setenv(
            "TENANT_SERVICE_RBAC_CHECK_URL",
            "http://tenant-service:8000/api/internal/v1/rbac/check/",
        )

        monkeypatch.delenv(
            "TENANT_SERVICE_INTERNAL_SERVICE_KEY",
            raising=False,
        )

        request = self._build_request()

        result = self.permission.has_permission(
            request,
            self.view,
        )

        assert result is False
        mock_post.assert_not_called()

    @patch("apps.common.rbac.requests.post")
    def test_sends_internal_service_key(
        self,
        mock_post,
        monkeypatch,
    ):
        monkeypatch.setenv(
            "TENANT_SERVICE_RBAC_CHECK_URL",
            "http://tenant-service:8000/api/internal/v1/rbac/check/",
        )

        monkeypatch.setenv(
            "TENANT_SERVICE_INTERNAL_SERVICE_KEY",
            "test-secret",
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "allowed": True,
        }

        mock_post.return_value = mock_response

        request = self._build_request()

        result = self.permission.has_permission(
            request,
            self.view,
        )

        assert result is True

        call_kwargs = mock_post.call_args.kwargs

        assert call_kwargs["headers"] == {
            "X-Internal-Service-Key": "test-secret",
        }

    @patch("apps.common.rbac.requests.post")
    def test_uses_configured_rbac_url(
        self,
        mock_post,
        monkeypatch,
    ):
        rbac_url = (
            "http://tenant-service:8000/"
            "api/internal/v1/rbac/check/"
        )

        monkeypatch.setenv(
            "TENANT_SERVICE_RBAC_CHECK_URL",
            rbac_url,
        )

        monkeypatch.setenv(
            "TENANT_SERVICE_INTERNAL_SERVICE_KEY",
            "test-secret",
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "allowed": True,
        }

        mock_post.return_value = mock_response

        request = self._build_request()

        result = self.permission.has_permission(
            request,
            self.view,
        )

        assert result is True

        assert mock_post.call_args.args[0] == rbac_url