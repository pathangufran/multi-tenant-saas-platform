from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import (
    FeatureCreateSerializer,
    FeatureResponseSerializer,
    FeatureUpdateSerializer,
    LimitCheckSerializer,
    LimitCheckResultSerializer,
    PlanFeatureCreateSerializer,
    PlanFeatureUpdateSerializer,
    PlanFeatureResponseSerializer,
    TenantEntitlementsSerializer,   
)
from .services import EntitlementService

class AdminFeatureCreateView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def post(self,request):
        serializer = FeatureCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        feature = EntitlementService.create_feature(
            **serializer.validated_data,
        )
        response = FeatureResponseSerializer(feature)
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        
class AdminFeatureListView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def get(self,request):
        
        features = EntitlementService.list_features(
            active_only=False
        )
        response = FeatureResponseSerializer(
            features,
            many=True,    
        )
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        
class AdminFeatureUpdateView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def patch(self,request,feature_id):
        serializer = FeatureUpdateSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        
        feature = EntitlementService.update_feature(
            feature_id=feature_id,
            data=serializer.validated_data,
        )
        response = FeatureResponseSerializer(feature)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminPlanFeatureCreateView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def post(self,request):
        serializer = PlanFeatureCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        plan_feature = (
            EntitlementService.set_plan_feature(
                **serializer.validated_data,
            )
        )
        response = PlanFeatureResponseSerializer(
            plan_feature,
        )
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        
class AdminPlanFeatureListView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def get(self,request,plan_id):
        
        plan_features = (
            EntitlementService.list_plan_features(
                plan_id=plan_id,        
            )
        )
        response = PlanFeatureResponseSerializer(
            plan_features,
            many=True,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminPlanFeatureDetailView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def get(self,request,plan_id,feature_id):
        plan_feature = (
                EntitlementService.get_plan_feature(
                    plan_id=plan_id,
                    feature_id=feature_id,
            )
        )
        response = PlanFeatureResponseSerializer(
            plan_feature,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminPlanFeatureUpdateView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def patch(self,request,plan_id,feature_id):
        serializer = PlanFeatureUpdateSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        
        plan_feature = PlanFeatureUpdateSerializer(
            plan_id=plan_id,
            feature_id=feature_id,
            data=serializer.validated_data,
        )
        response = PlanFeatureResponseSerializer(
            plan_feature
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminTenantEntitlementsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        tenant_id = request.tenant_context.tenant_id

        result = (
                EntitlementService.get_tenant_entitlements(
                    tenant_id=tenant_id,
            )
        )
        response = TenantEntitlementsSerializer(
            result,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )

class AdminLimitCheckView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = LimitCheckSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)

        entitlement = EntitlementService.check_limit(
            **serializer.validated_data,
        ) 
        response = LimitCheckResultSerializer(
            entitlement,
        ) 

        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )