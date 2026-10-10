from rest_framework import status
from rest_framework.permissions import AllowAny,IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import (
    PlanCreateSerializer,
    PlanResponseSerializer,
)
from .services import PlanService

class PublicPlanListView(APIView):
    
    permission_classes = [AllowAny]
    
    def get(self,request):
        
        plans = PlanService.list_plans(
            public_only=True,
        )
        response = PlanResponseSerializer(
            plans,
            many=True,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class PublicPlanDetailView(APIView):
    
    permission_classes = [AllowAny]
    
    def get(self,request,code):
        
        plan = PlanService.get_plan_by_code(
            code,
            public_only=True,
        )
        response = PlanResponseSerializer(plan)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminPlanCreateView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def post(self,request):
        serializer = PlanCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        plan = PlanService.create_plan(
            **serializer.validated_data,
        )
        response = PlanResponseSerializer(plan)
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        
class AdminPlanListView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def get(self,request):
        
        plans = PlanService.list_plans(
            public_only=False,
        )
        response = PlanResponseSerializer(
            plans,
            many=True,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminPlanDetailView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def get(self,request,plan_id):
        
        plan = PlanService.get_plan_by_id(
            plan_id,
        )
        response = PlanResponseSerializer(plan)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminPlanUpdateView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def patch(self,request,plan_id):
        serializer = PlanCreateSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        
        plan = PlanService.update_plan(
            plan_id,
            serializer.validated_data,
        )
        response = PlanResponseSerializer(plan)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminPlanDeleteView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def delete(self,request,plan_id):
        
        plan = PlanService.delete_plan(
            plan_id,
        )
        
        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )
        