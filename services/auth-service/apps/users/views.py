from rest_framework import status
from rest_framework.views import APIView   
from rest_framework.response import Response
from .serializers import (
    UserRegistrationSerializer,
    UserRegistrationResponseSerializer,
)
from .services import UserService
from apps.common.rate_limit import RateLimiter
from apps.authentication.security_service import (
    AuthenticationSecurityService,
)

class UserRegistrationView(APIView):

    def post(self,request):
        serializer = UserRegistrationSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        AuthenticationSecurityService.check_registration_limit(
            ip_address=RateLimiter.get_client_ip(request),
        )
        user = UserService.register_user(
            **serializer.validated_data,
        )
        response = UserRegistrationResponseSerializer(
            user
        )

        return Response(
            response.data,
            status=status.HTTP_201_CREATED,
        )

    