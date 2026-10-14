from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import (
    InvoiceGenerateSerializer,
    InvoiceListQuerySerializer,
    InvoiceResponseSerializer,   
)
from .services import InvoiceService

class AdminInvoiceCreateView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def post(self,request):
        serializer = InvoiceGenerateSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        invoice = InvoiceService.generate_invoice(
            **serializer.validated_data,
        )
        response = InvoiceResponseSerializer(invoice)
        
        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )
        
class AdminInvoiceListView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def get(self,request):
        serializer = InvoiceListQuerySerializer(
            data=request.query_params            
        )
        serializer.is_valid(raise_exception=True)
        
        invoices = InvoiceService.list_invoices(
            **serializer.validated_data
        )
        response = InvoiceResponseSerializer(
            invoices,
            many=True,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminInvoiceDetailView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def get(self,request,invoice_id):
        invoice = InvoiceService.get_invoice(
            invoice_id,
        )
        response = InvoiceResponseSerializer(invoice)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminInvoiceNumberDetailView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def get(self,request,invoice_number):
        invoice = InvoiceService.get_invoice_by_number(
            invoice_number,
        )
        response = InvoiceResponseSerializer(invoice)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class AdminInvoiceVoidView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def patch(self,request,invoice_id):
        invoice = InvoiceService.void_invoice(
            invoice_id,
            
        )
        response = InvoiceResponseSerializer(
            invoice,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
        