from rest_framework import status
from rest_framework.views import APIView 
from rest_framework.response import Response
from .serializers import (
    LoginSerializer,
    LoginResponseSerializer,
    LogoutSerializer,
    LogoutResponseSerializer,
    TokenRefreshSerializer,
    TokenRefreshResponseSerializer,
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
        response = LoginResponseSerializer(tokens,)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class TokenRefreshView(APIView):
    
    def post(self,request):
        serializer = TokenRefreshSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        tokens = AuthenticationService.refresh_token(
            **serializer.validated_data,
        )
        response = (
            TokenRefreshResponseSerializer(tokens)
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
class LogoutView(APIView):
    
    def post(self,request):
        serializer = LogoutSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        AuthenticationService.logout(
            **serializer.validated_data
        )
        response = LogoutResponseSerializer(
            {
                "message": "Successfully logged out.",
            }
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )