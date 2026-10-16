from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import (
    BillingEventSerializer,
    BillingEventDeliverySerializer,
)
from .services import (
    BillingIntegrationService,
)

class AdminBillingEventListView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def get(self,request):
        tenant_id = request.tenant_context.tenant_id
        
        events = (
            BillingIntegrationService.list_events(
                tenant_id,        
            )
        )
        response = BillingEventSerializer(
            events,
            many=True,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminBillingEventDetailView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def get(self,request,event_id):
        event = BillingIntegrationService.get_event(
            event_id
        )
        response = BillingEventSerializer(
            event
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminBillingEventRetryView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def post(self,request,event_id):
        result = (
            BillingIntegrationService.
            retry_event(event_id)
        )
        
        if result["status"] == "not_found":
            return Response(
                {"detail": "Billing event not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
            
        event = BillingIntegrationService.get_event(
            event_id
        )
        response = BillingEventSerializer(event)
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )