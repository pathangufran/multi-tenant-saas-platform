from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import (
    PaymentCreateSerializer,
    PaymentListQuerySerializer,
    PaymentResponseSerializer,
)
from .services import PaymentService

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