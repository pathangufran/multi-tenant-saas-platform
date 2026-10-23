from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.health_checks import HealthCheckService
from apps.common.health_serializers import (
    LivenessSerializer,
    ReadinessSerializer,
)

class HealthView(APIView):
    
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        data = HealthCheckService.liveness()
        serializer = LivenessSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

class ReadinessView(APIView):
    
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        data = HealthCheckService.readiness()
        serializer = ReadinessSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        response_status = (
            status.HTTP_200_OK
            if data["status"] == "ready"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return Response(
            serializer.data,
            status=response_status,
        )
