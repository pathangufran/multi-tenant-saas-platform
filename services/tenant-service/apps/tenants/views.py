from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import (
    MembershipRoleSerializer,
    ObjectPermissionCreateSerializer,
    RoleObjectPermissionCreateSerializer,
    RoleResponseSerializer,
    TenantCreateSerializer,
    TenantUpdateSerializer,
    TenantResponseSerializer,
    TenantRoleCreateSerializer,
    TenantRoleUpdateSerializer,
)
from .services import TenantService
from .rbac_service import (
    ObjectPermissionService,
    TenantRoleService,
)
from .membership_service import (
    TenantMembershipRoleService,
)
from .permissions import RBACPermission
from apps.common.exceptions import (
    ResourceNotFoundError,
)

class TenantCreateView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=["Tenants"],
        request=TenantCreateSerializer,
        responses={
            201: TenantResponseSerializer,
        },
        description=(
            "Create a tenant and establish an "
            "active owner membership for the "
            "authenticated user."
        ),
    )
    def post(self,request):
        
        serializer = TenantCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            tenant = TenantService.create_tenant(
                name=serializer.validated_data["name"],
                slug=serializer.validated_data["slug"],
                owner_user_id=request.user.id,
            )
        except ValueError as exc:
            return Response(
                data={"details":str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        response = TenantResponseSerializer(tenant)
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        
class TenantListView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=["Tenants"],
        responses=TenantResponseSerializer(many=True),
        description=(
            "Return all active tenant memberships "
            "belonging to the authenticated user."
        ),
    )
    def get(self,request):
        
        tenants = TenantService.get_user_tenants(
            user_id=request.user.id,
        )
        serializer = TenantResponseSerializer(
            tenants,
            many=True,
        )
        
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,    
        )
        
class CurrentTenantView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=["Tenants"],
        responses={
            200: TenantResponseSerializer,
            404: OpenApiResponse(
                description="Tenant not found."
            ),
        },
        description=(
            "Retrieve a tenant accessible to "
            "the authenticated user."
        ),
    )
    def get(self,request,tenant_id):
        
        try:
            tenant = TenantService.get_user_tenant(
                user_id=request.user.id,
                tenant_id=tenant_id,
            )
        except ResourceNotFoundError as exc:
            return Response(
                data={"details": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
            
        serializer = TenantResponseSerializer(tenant)
        
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
        
    @extend_schema(
        tags=["Tenants"],
        request=TenantUpdateSerializer,
        responses={
            200: TenantResponseSerializer,
            404: OpenApiResponse(
                description="Tenant not found."
            ),
        },
        description=(
            "Update tenant name and/or slug."
        ),
    )
    def patch(self,request,tenant_id):
        
        serializer = TenantUpdateSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            tenant = TenantService.update_tenant(
                tenant_id=tenant_id,
                user_id=request.user.id,
                name = serializer.validated_data.get("name"),
                slug = serializer.validated_data.get("slug")
            )
        except ResourceNotFoundError as exc:
            return Response(
                data={"details": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as exc:
            return Response(
                data={"details": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
        response = TenantResponseSerializer(tenant)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class TenantSuspendView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=["Tenants"],
        responses={
            200: TenantResponseSerializer,
            404: OpenApiResponse(
                description="Tenant not found."
            ),
        },
        description="Suspend an active tenant.",
    )
    def post(self,request,tenant_id):
        
        try:
            tenant = TenantService.suspend_tenant(
                tenant_id=tenant_id,
                user_id=request.user.id,
            )
        except ResourceNotFoundError as exc:
            return Response(
                data={"details": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as exc:
            return Response(
                data={"details": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        serializer = TenantResponseSerializer(tenant)
        
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
        
class TenantActivateView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        tags=["Tenants"],
        responses={
            200: TenantResponseSerializer,
            404: OpenApiResponse(
                description="Tenant not found."
            ),
        },
        description="Activate a tenant.",
    )
    def post(self,request,tenant_id):
        
        try:
            tenant = TenantService.activate_tenant(
                tenant_id=tenant_id,
                user_id=request.user.id,
            )
        except ValueError as exc:
            return Response(
                data={"details":str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        serializer = TenantResponseSerializer(tenant)
        
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
        
class TenantDeactivateView(APIView):
    
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Tenants"],
        responses={
            200: TenantResponseSerializer,
            404: OpenApiResponse(
                description="Tenant not found."
            ),
        },
        description="Deactivate a tenant.",
    )
    def post(self,request,tenant_id):
        
        try:
            tenant = TenantService.deactivate_tenant(
                tenant_id=tenant_id,
                user_id=request.user.id,
            )
        except ValueError as exc:
            return Response(
                data={"details":str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = TenantResponseSerializer(tenant)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,    
        )
        
class TenantRoleListCreateView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        RBACPermission,
    ]
    required_permission = "users.read"
    
    @extend_schema(
        responses=RoleResponseSerializer(
            many=True
        ),
    )
    def get(self,request):
        
        tenant_id = request.tenant_context.tenant_id
        roles = TenantRoleService.list_roles(
            tenant_id=tenant_id,
        )
        
        serializer = RoleResponseSerializer(
            roles,
            many=True,
        )
        
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
        
    @extend_schema(
        request=TenantRoleCreateSerializer,
        responses=RoleResponseSerializer,
    )
    def post(self,request):
        serializer = TenantRoleCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        tenant_id = request.tenant_context.tenant_id
        role = TenantRoleService.create_role(
            tenant_id=tenant_id,
            name=serializer.validated_data["name"],
            code=serializer.validated_data["code"],
            description=serializer.validated_data.get(
                "description",
                "",
            ),
            permission_codes = serializer.validated_data.get(
                "permission_codes",
                [],
            ),
            
        )
        
        response = RoleResponseSerializer(role,)
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )

class TenantRoleDetailView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        RBACPermission,
    ]
    
    required_permission = "users.update"
    
    @extend_schema(
        responses=RoleResponseSerializer,
    )
    def get(self,request,role_id):
        
        tenant_id = request.tenant_context.tenant_id
        role = TenantRoleService.get_role(
            tenant_id=tenant_id,
            role_id=role_id,
            
        )
        
        serializer = RoleResponseSerializer(role,)
        
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
        
    @extend_schema(
        request=TenantRoleUpdateSerializer,
        responses=RoleResponseSerializer,
    )
    def patch(self,request,role_id):
        serializer = TenantUpdateSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True,)
        
        tenant_id = request.tenant_context.tenant_id
        role = TenantRoleService.update_role(
            tenant_id=tenant_id,
            role_id=role_id,
            name=serializer.validated_data.get(
                "name",
            ),
            description=serializer.validated_data.get(
                "description",
            ),
            permission_codes=serializer.validated_data.get(
                "permission_codes",
            ),
            
        )
        
        response = RoleResponseSerializer(role,)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
    def delete(self,request,role_id):
        tenant_id = request.tenant_context.tenant_id

        TenantRoleService.delete_role(
            tenant_id=tenant_id,
            role_id=role_id,
        )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )
        
class MembershipRoleView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        RBACPermission,
    ]
    
    required_permission = "users.update"
    
    @extend_schema(
        request=MembershipRoleSerializer,
        responses=RoleResponseSerializer,
    )
    def post(self,request,membership_id):
        serializer = MembershipRoleSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True,)
        
        tenant_id = request.tenant_context.tenant_id
        membership = (
            TenantMembershipRoleService.assign_role(
                tenant_id=tenant_id,
                membership_id=membership_id,
                role_id=serializer.validated_data[
                    "role_id"
                ],
            )
        )
        
        response = RoleResponseSerializer(
            membership.role,
        )

        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
    def delete(self,request,membership_id):
        
        tenant_id = request.tenant_context.tenant_id
        membership = (
            TenantMembershipRoleService.remove_role(
                tenant_id=tenant_id,
                membership_id=membership_id,
            )
        )
        
        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )
        
class UserObjectPermissionView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        RBACPermission,
    ]
    
    required_permission = "users.update"
    
    @extend_schema(
        request=ObjectPermissionCreateSerializer,
    )
    def post(self,request):
        serializer = ObjectPermissionCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True,)
        
        tenant_id = request.tenant_context.tenant_id

        object_permission = (
            ObjectPermissionService
            .grant_user_permission(
                tenant_id=tenant_id,
                user_id=serializer.validated_data["user_id"],
                resource_type=serializer.validated_data["resource_type"],
                resource_id=serializer.validated_data["resource_id"],
                permission_code=serializer.validated_data["permission_code"],
            )
        )
        
        return Response(
            {
                "id": object_permission.id,
                "message": (
                    "Object permission granted."
                ),
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self,request):
        serializer = ObjectPermissionCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True,)
        
        tenant_id = request.tenant_context.tenant_id
        removed = (
            ObjectPermissionService
            .revoke_user_permission(
                tenant_id=tenant_id,
                user_id=serializer.validated_data["user_id"],
                resource_type=serializer.validated_data["resource_type"],
                resource_id=serializer.validated_data["resource_id"],
                permission_code=serializer.validated_data["permission_code"],
            )
        )
        
        return Response(
            {
                "removed": removed,
            },
            status=status.HTTP_200_OK,
        )
    
class RoleObjectPermissionView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        RBACPermission,
    ]
    
    required_permission = "users.update"
    
    @extend_schema(
        request=RoleObjectPermissionCreateSerializer,
    )
    def post(self, request):
        serializer = (
            RoleObjectPermissionCreateSerializer(
                data=request.data,
            )
        )

        serializer.is_valid(raise_exception=True,)

        tenant_id = request.tenant_context.tenant_id
        object_permission = (
            ObjectPermissionService
            .grant_role_permission(
                tenant_id=tenant_id,
                role_id=serializer.validated_data["role_id"],
                resource_type=serializer.validated_data["resource_type"],
                resource_id=serializer.validated_data["resource_id"],
                permission_code=serializer.validated_data["permission_code"],
            )
        )

        return Response(
            {
                "id": object_permission.id,
                "message": (
                    "Role object permission granted."
                ),
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request):
        serializer = (
            RoleObjectPermissionCreateSerializer(
                data=request.data,
            )
        )

        serializer.is_valid(raise_exception=True,)

        tenant_id = request.tenant_context.tenant_id
        removed = (
            ObjectPermissionService
            .revoke_role_permission(
                tenant_id=tenant_id,
                role_id=serializer.validated_data["role_id"],
                resource_type=serializer.validated_data["resource_type"],
                resource_id=serializer.validated_data["resource_id"],
                permission_code=serializer.validated_data["permission_code"],
            )
        )

        return Response(
            {
                "removed": removed,
            },
            status=status.HTTP_200_OK,
        )