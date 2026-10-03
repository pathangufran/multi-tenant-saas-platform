# import os
# import pytest
# from uuid import uuid4
# from types import SimpleNamespace
# from unittest.mock import patch

# @pytest.mark.django_db
# class TestInternalRBACPermissionCheckView:
#     def setup_method(self):
#         self.user_id = uuid4()
#         self.tenant_id = uuid4()

#         self.service_key = os.getenv(
#             "INTERNAL_SERVICE_KEY",
#             "test-internal-service-key",
#         )

#         self.tenant_service_url = os.getenv(
#             "TENANT_SERVICE_URL",
#             "http://localhost:8001",
#         )

#     def _build_request(
#         self,
#         *,
#         data=None,
#         service_key=None,
#     ):
#         request = self.factory.post(
#             "/api/internal/v1/rbac/check/",
#             data=data or {},
#             format="json",
#         )

#         if service_key is not None:
#             request.headers["X-Internal-Service-Key"] = service_key

#         return request

#     @patch(
#         "apps.tenants.rbac_internal_views."
#         "PermissionCheckService.has_permission"
#     )
#     def test_allows_valid_internal_permission_check(
#         self,
#         mock_has_permission,
#         settings,
#         monkeypatch,
#     ):
#         monkeypatch.setenv(
#             "INTERNAL_SERVICE_KEY",
#             self.service_key,
#         )

#         mock_has_permission.return_value = True

#         request = self._build_request(
#             data={
#                 "user_id": str(self.user_id),
#                 "tenant_id": str(self.tenant_id),
#                 "permission_code": "projects.read",
#             },
#             service_key=self.service_key,
#         )

#         response = self.view(request)

#         assert response.status_code == 200
#         assert response.data == {
#             "allowed": True,
#         }

#         mock_has_permission.assert_called_once_with(
#             user_id=str(self.user_id),
#             tenant_id=str(self.tenant_id),
#             permission_code="projects.read",
#         )

#     @patch(
#         "apps.tenants.rbac_internal_views."
#         "PermissionCheckService.has_permission"
#     )
#     def test_returns_false_when_permission_is_denied(
#         self,
#         mock_has_permission,
#         monkeypatch,
#     ):
#         monkeypatch.setenv(
#             "INTERNAL_SERVICE_KEY",
#             self.service_key,
#         )

#         mock_has_permission.return_value = False

#         request = self._build_request(
#             data={
#                 "user_id": str(self.user_id),
#                 "tenant_id": str(self.tenant_id),
#                 "permission_code": "projects.delete",
#             },
#             service_key=self.service_key,
#         )

#         response = self.view(request)

#         assert response.status_code == 200
#         assert response.data == {
#             "allowed": False,
#         }

#         mock_has_permission.assert_called_once_with(
#             user_id=str(self.user_id),
#             tenant_id=str(self.tenant_id),
#             permission_code="projects.delete",
#         )

#     @patch(
#         "apps.tenants.rbac_internal_views."
#         "PermissionCheckService.has_permission"
#     )
#     def test_rejects_invalid_internal_service_key(
#         self,
#         mock_has_permission,
#         monkeypatch,
#     ):
#         monkeypatch.setenv(
#             "INTERNAL_SERVICE_KEY",
#             self.service_key,
#         )

#         request = self._build_request(
#             data={
#                 "user_id": str(self.user_id),
#                 "tenant_id": str(self.tenant_id),
#                 "permission_code": "projects.read",
#             },
#             service_key="wrong-service-key",
#         )

#         response = self.view(request)

#         assert response.status_code == 403
#         assert response.data == {
#             "detail": "Invalid internal service credentials.",
#         }

#         mock_has_permission.assert_not_called()

#     @patch(
#         "apps.tenants.rbac_internal_views."
#         "PermissionCheckService.has_permission"
#     )
#     def test_rejects_missing_internal_service_key(
#         self,
#         mock_has_permission,
#         monkeypatch,
#     ):
#         monkeypatch.setenv(
#             "INTERNAL_SERVICE_KEY",
#             self.service_key,
#         )

#         request = self._build_request(
#             data={
#                 "user_id": str(self.user_id),
#                 "tenant_id": str(self.tenant_id),
#                 "permission_code": "projects.read",
#             },
#         )

#         response = self.view(request)

#         assert response.status_code == 403
#         assert response.data == {
#             "detail": "Invalid internal service credentials.",
#         }

#         mock_has_permission.assert_not_called()

#     @patch(
#         "apps.tenants.rbac_internal_views."
#         "PermissionCheckService.has_permission"
#     )
#     def test_rejects_when_internal_service_key_is_not_configured(
#         self,
#         mock_has_permission,
#         monkeypatch,
#     ):
#         monkeypatch.delenv(
#             "INTERNAL_SERVICE_KEY",
#             raising=False,
#         )

#         request = self._build_request(
#             data={
#                 "user_id": str(self.user_id),
#                 "tenant_id": str(self.tenant_id),
#                 "permission_code": "projects.read",
#             },
#             service_key=self.service_key,
#         )

#         response = self.view(request)

#         assert response.status_code == 403
#         assert response.data == {
#             "detail": "Invalid internal service credentials.",
#         }

#         mock_has_permission.assert_not_called()

#     @patch(
#         "apps.tenants.rbac_internal_views."
#         "PermissionCheckService.has_permission"
#     )
#     def test_rejects_missing_user_id(
#         self,
#         mock_has_permission,
#         monkeypatch,
#     ):
#         monkeypatch.setenv(
#             "INTERNAL_SERVICE_KEY",
#             self.service_key,
#         )

#         request = self._build_request(
#             data={
#                 "tenant_id": str(self.tenant_id),
#                 "permission_code": "projects.read",
#             },
#             service_key=self.service_key,
#         )

#         response = self.view(request)

#         assert response.status_code == 400
#         assert response.data == {
#             "detail": "user_id is required.",
#         }

#         mock_has_permission.assert_not_called()

#     @patch(
#         "apps.tenants.rbac_internal_views."
#         "PermissionCheckService.has_permission"
#     )
#     def test_rejects_missing_tenant_id(
#         self,
#         mock_has_permission,
#         monkeypatch,
#     ):
#         monkeypatch.setenv(
#             "INTERNAL_SERVICE_KEY",
#             self.service_key,
#         )

#         request = self._build_request(
#             data={
#                 "user_id": str(self.user_id),
#                 "permission_code": "projects.read",
#             },
#             service_key=self.service_key,
#         )

#         response = self.view(request)

#         assert response.status_code == 400
#         assert response.data == {
#             "detail": "tenant_id is required.",
#         }

#         mock_has_permission.assert_not_called()

#     @patch(
#         "apps.tenants.rbac_internal_views."
#         "PermissionCheckService.has_permission"
#     )
#     def test_rejects_missing_permission_code(
#         self,
#         mock_has_permission,
#         monkeypatch,
#     ):
#         monkeypatch.setenv(
#             "INTERNAL_SERVICE_KEY",
#             self.service_key,
#         )

#         request = self._build_request(
#             data={
#                 "user_id": str(self.user_id),
#                 "tenant_id": str(self.tenant_id),
#             },
#             service_key=self.service_key,
#         )

#         response = self.view(request)

#         assert response.status_code == 400
#         assert response.data == {
#             "detail": "permission_code is required.",
#         }

#         mock_has_permission.assert_not_called()