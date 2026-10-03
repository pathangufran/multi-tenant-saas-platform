from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .serializers import (
    TeamCreateSerializer,
    TeamUpdateSerializer,
    TeamResponseSerializer,
)
from .services import TeamService
from apps.common.rbac import TenantServiceRBACPermission

class TeamCreateView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "teams.create"
    
    def post(self,request):
        tenant_id = request.tenant_context.tenant_id
        user_id = request.authenticated_user_id
        
        serializer = TeamCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        team = TeamService.create_team(
            tenant_id=tenant_id,
            user_id=user_id,
            **serializer.validated_data,
        )
        response = TeamResponseSerializer(team)
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        
class TeamListView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "teams.read"
    
    def get(self,request):
        tenant_id = request.tenant_context.tenant_id
        
        teams = TeamService.list_teams(
            tenant_id=tenant_id,    
        )
        response = TeamResponseSerializer(
            teams,
            many=True,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class TeamDetailView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "teams.read"
    
    def get(self,request,team_id):
        tenant_id = request.tenant_context.tenant_id
        
        team = TeamService.get_team(
            tenant_id=tenant_id,
            team_id=team_id,
        )
        response = TeamResponseSerializer(team)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class TeamUpdateView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "teams.update"
    
    def patch(self,request,team_id):
        tenant_id = request.tenant_context.tenant_id
        
        serializer = TeamUpdateSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        
        team = TeamService.update_team(
            tenant_id=tenant_id,
            team_id=team_id,
            data=serializer.validated_data,
        )
        response = TeamResponseSerializer(team)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class TeamDeleteView(APIView):
    
    permission_classes = [
        IsAuthenticated,
        TenantServiceRBACPermission,    
    ]
    required_permission = "teams.delete"
    
    def delete(self,request,team_id):
        tenant_id = request.tenant_context.tenant_id
        
        team = TeamService.delete_team(
            tenant_id=tenant_id,
            team_id=team_id,
        )
        
        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )
        