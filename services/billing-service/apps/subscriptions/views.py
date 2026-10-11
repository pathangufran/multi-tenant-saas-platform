from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from .serializers import (
    SubscriptionCreateSerializer,
    SubscriptionCancelSerializer,
    SubscriptionResponseSerializer,
)
from .services import SubscriptionService

class AdminSubscriptionCreateView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def post(self,request):
        serializer = SubscriptionCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        subscription = SubscriptionService.create_subscription(
            **serializer.validated_data,   
        )
        response = SubscriptionResponseSerializer(
            subscription,
        )
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        
class AdminSubscriptionListView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def get(self,request):
        tenant_id = request.tenant_context.tenant_id
        subscriptions = SubscriptionService.list_subscriptions(
            tenant_id,            
        )
        response = SubscriptionResponseSerializer(
            subscriptions,
            many=True,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminSubscriptionDetailView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def get(self,request,subscription_id):
        subscription = SubscriptionService.get_subscription(
            subscription_id,
        )
        response = SubscriptionResponseSerializer(
            subscription,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminSubscriptionCancelView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def post(self,request,subscription_id):
        serializer = SubscriptionCancelSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        subscription = SubscriptionService.cancel_subscription(
            subscription_id,
            **serializer.validated_data,
        )
        response = SubscriptionResponseSerializer(
            subscription,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminSubscriptionRenewView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def post(self,request,subscription_id):
        subscription = SubscriptionService.renew_subscription(
            subscription_id,
        )
        response = SubscriptionResponseSerializer(
            subscription,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )