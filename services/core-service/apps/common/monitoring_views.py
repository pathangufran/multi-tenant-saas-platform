from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.common.celery_monitoring import (
    CeleryMonitoringService,
)
from apps.common.monitoring_serializers import (
    CeleryMonitoringSerializer,
)

class AdminCeleryMonitoringView(APIView):
    
    permission_classes = [IsAdminUser]
    
    def get(self,request):
        data = CeleryMonitoringService.get_status()
        serializer = CeleryMonitoringSerializer(
            data=data
        )
        serializer.is_valid(raise_exception=True)
        
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )