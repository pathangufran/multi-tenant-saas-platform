import json
from rest_framework import status
from rest_framework.permissions import (
    IsAdminUser,
    AllowAny,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import (
    PaymentCreateSerializer,
    PaymentListQuerySerializer,
    PaymentResponseSerializer,
    PaymentWebhookSerializer,
)
from .services import (
    PaymentService,
    PaymentWebhookService,
)

class AdminPaymentCreateView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def post(self,request):
        serializer = PaymentCreateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        payment = PaymentService.create_payment(
            **serializer.validated_data,
        )
        response = PaymentResponseSerializer(payment)
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        
class AdminPaymentListView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def get(self,request):
        serializer = PaymentListQuerySerializer(
            data=request.query_params,
        )
        serializer.is_valid(raise_exception=True)
        
        payments = PaymentService.list_payments(
            **serializer.validated_data,
        )
        response = PaymentResponseSerializer(
            payments,
            many=True,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminPaymentDetailView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def get(self,request,payment_id):
        payment = PaymentService.get_payment(
            payment_id,
        )
        response = PaymentResponseSerializer(
            payment,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class PaymentWebhookView(APIView):
    
    permission_classes = [AllowAny]
    authentication_classes = []
    
    def post(self,request):
        request_data = json.loads(request.body)
        serializer = PaymentWebhookSerializer(
            data=request_data,
        )
        serializer.is_valid(raise_exception=True)
        
        webhook = PaymentWebhookService.process_event(
            provider="MOCK",
            raw_body=request.body,
            signature=request_data["signature"],
            validated_data=serializer.validated_data,
            payload=request_data,
        )
        
        if webhook.get("error") == "payment_not_found":
            return Response(
                {
                    "detail": "Payment not found.",
                    "event_id": webhook["event"].event_id,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if webhook.get("error") == "invalid_transition":
            return Response(
                {
                    "detail": webhook["event"].error_message,
                    "event_id": webhook["event"].event_id,
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "event_id": webhook["event"].event_id,
                "status": webhook["event"].status,
                "duplicate": webhook["duplicate"],
            },
            status=status.HTTP_200_OK,
        )