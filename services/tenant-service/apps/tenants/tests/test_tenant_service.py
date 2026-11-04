# import pytest
# from apps.tenants.models import Tenant
# from apps.tenants.services import TenantService

# @pytest.mark.django_db
# class TestTenantService:

#     def test_create_tenant(self):
#         tenant = TenantService.create_tenant(
#             name="Acme Corporation",
#             slug="acme",
#         )

#         assert tenant.name == "Acme Corporation"
#         assert tenant.slug == "acme"
#         assert tenant.status == Tenant.Status.ACTIVE

#     def test_create_tenant_strips_name(self):
#         tenant = TenantService.create_tenant(
#             name="  Acme Corporation  ",
#             slug="acme",
#         )

#         assert tenant.name == "Acme Corporation"

#     def test_create_tenant_normalizes_slug(self):
#         tenant = TenantService.create_tenant(
#             name="Acme Corporation",
#             slug="Acme Corporation",
#         )

#         assert tenant.slug == "acme-corporation"

#     def test_duplicate_slug_is_rejected(self):
#         TenantService.create_tenant(
#             name="Acme Corporation",
#             slug="acme",
#         )

#         with pytest.raises(ValueError, match="already exists"):
#             TenantService.create_tenant(
#                 name="Another Acme",
#                 slug="ACME",
#             )

#     def test_empty_name_is_rejected(self):
#         with pytest.raises(
#             ValueError,
#             match="Tenant name is required",
#         ):
#             TenantService.create_tenant(
#                 name="   ",
#                 slug="acme",
#             )

#     def test_empty_slug_is_rejected(self):
#         with pytest.raises(
#             ValueError,
#             match="Tenant slug is required",
#         ):
#             TenantService.create_tenant(
#                 name="Acme Corporation",
#                 slug="---",
#             )

#     def test_created_tenant_is_persisted(self):
#         tenant = TenantService.create_tenant(
#             name="Acme Corporation",
#             slug="acme",
#         )

#         assert Tenant.objects.filter(
#             id=tenant.id,
#         ).exists()