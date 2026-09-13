from rest_framework import status
from rest_framework.views import APIView 
from rest_framework.response import Response
from .serializers import (
    LoginSerializer,
    LoginResponseSerializer,
)
from .services import AuthenticationService

class LoginView(APIView):
    
    def post(self,request):
        serializer = LoginSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True,)
        
        tokens = AuthenticationService.login(
            **serializer.validated_data,
        )
        response = LoginResponseSerializer(
            tokens,
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )