from rest_framework import status
from rest_framework.views import APIView 
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import (
    LoginSerializer,
    LoginResponseSerializer,
    LogoutSerializer,
    LogoutResponseSerializer,
    TokenRefreshSerializer,
    TokenRefreshResponseSerializer,
    CurrentUserSerializer,
    PasswordChangeSerializer,
    PasswordChangeResponseSerializer,
    EmailVerificationSendSerializer,
    EmailVerificationVerifySerializer,
    EmailVerificationResponseSerializer,
)
from .services import AuthenticationService
from .email_verification_service import (
    EmailVerificationService,
)
from apps.common.rate_limit import RateLimiter
from .security_service import (
    AuthenticationSecurityService,
)
from apps.common.middleware import request_id_context
from drf_spectacular.utils import extend_schema

@extend_schema(
    request=LoginSerializer,
    responses={
        200: LoginResponseSerializer,
        400: None,
        401: None,
        429: None,
    },
    tags=["Authentication"],
)
class LoginView(APIView):
    
    def post(self,request):
        serializer = LoginSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True,)
        email = serializer.validated_data["email"]
        
        AuthenticationSecurityService.check_login_limits(
            ip_address=RateLimiter.get_client_ip(request),
            email=email,
        )
        
        tokens = AuthenticationService.login(
            **serializer.validated_data,
            ip_address=RateLimiter.get_client_ip(request),
            request_id=request_id_context.get(),
        )
        response = LoginResponseSerializer(tokens,)
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
@extend_schema(
    request=TokenRefreshSerializer,
    responses={
        200: TokenRefreshResponseSerializer,
        400: None,
        401: None,
    },
    tags=["Authentication"],
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
        
@extend_schema(
    request=LogoutSerializer,
    responses={
        200: LogoutResponseSerializer,
        400: None,
        401: None,
    },
    tags=["Authentication"],
)
class LogoutView(APIView):
    
    def post(self,request):
        serializer = LogoutSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        AuthenticationService.logout(
            **serializer.validated_data,
            user=(
                request.user if 
                request.user.is_authenticated 
                else None
            ),
            ip_address=RateLimiter.get_client_ip(request),
            request_id=request_id_context.get(),
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
        
@extend_schema(
    responses={
        200: CurrentUserSerializer,
        401: None,
    },
    tags=["Authentication"],
)
class CurrentUserView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def get(self,request):
        user = AuthenticationService.get_current_user(
            user=request.user,
        )
        serializer = CurrentUserSerializer(user)
        
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
        
@extend_schema(
    request=PasswordChangeSerializer,
    responses={
        200: PasswordChangeResponseSerializer,
        400: None,
        401: None,
        429: None,
    },
    tags=["Authentication"],
)
class PasswordChangeView(APIView):
    
    permission_classes = [IsAuthenticated]
    
    def post(self,request):
        serializer = PasswordChangeSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        AuthenticationSecurityService.check_password_change_limit(
            user_id=str(request.user.id),
        )
        
        AuthenticationService.change_password(
            user=request.user,
            **serializer.validated_data,
            ip_address=RateLimiter.get_client_ip(request),
            request_id=request_id_context.get(),
            
        )
        response = PasswordChangeResponseSerializer(
            {
                "message": "Password changed successfully.",
            }
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
@extend_schema(
    request=EmailVerificationSendSerializer,
    responses={
        200: EmailVerificationResponseSerializer,
        400: None,
        404: None,
        409: None,
        429: None,
    },
    tags=["Email Verification"],
)
class EmailVerificationSendView(APIView):
    
    def post(self,request):
        serializer = EmailVerificationSendSerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        AuthenticationSecurityService.check_verification_limit(
            ip_address=RateLimiter.get_client_ip(request),
        )
        
        EmailVerificationService.create_verification_token(
            **serializer.validated_data,
            ip_address=RateLimiter.get_client_ip(request),
            request_id=request_id_context.get(),
        )
        response = (
            EmailVerificationResponseSerializer(
                {
                    "message": (
                        "Email verification token \
                        generated successfully."
                    ),
                }
            )
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )
        
@extend_schema(
    request=EmailVerificationVerifySerializer,
    responses={
        200: EmailVerificationResponseSerializer,
        400: None,
        401: None,
        409: None,
    },
    tags=["Email Verification"],
)
class EmailVerificationVerifyView(APIView):
    
    def post(self,request):
        serializer = EmailVerificationVerifySerializer(
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        
        EmailVerificationService.verify_email(
            **serializer.validated_data,
            ip_address=RateLimiter.get_client_ip(request),
            request_id=request_id_context.get(),
        )
        response = (
            EmailVerificationResponseSerializer(
                {
                    "message": (
                        "Email verified successfully."
                    ),
                }
            )
        )
        
        return Response(
            response.data,
            status=status.HTTP_200_OK,
        )