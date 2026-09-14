from django.db import transaction
from apps.users.models import User
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import (
    TokenRefreshSerializer as JWTTokenRefreshSerializer
)
from apps.common.exceptions import AuthenticationError

class AuthenticationService:
    
    @classmethod
    def authenticated_user(
        cls,
        *,
        email: str,
        password: str,
    ) -> User:
        
        try:
            user = User.objects.get(
                email__iexact=email,
            )
        except User.DoesNotExist:
            raise AuthenticationError(
                message="Invalid email or password."
            )
            
        if not user.check_password(password):
            raise AuthenticationError(
                message="Invalid email or password."
            )
            
        if not user.is_active:
            raise AuthenticationError(
                message="Invalid email or password."
            )
            
        return user
    
    @staticmethod
    def generate_tokens(
        *,
        user: User,
    ) -> dict[str,str]:
        
        refresh = RefreshToken.for_user(user)
        
        return {
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "token_type": "Bearer",
        }
        
    @classmethod
    def login(
        cls,
        *,
        email: str,
        password: str,
    ) -> dict[str,str]:
        
        user = cls.authenticated_user(
            email=email,
            password=password,
        )
        
        return cls.generate_tokens(user=user)
    
    @staticmethod
    def refresh_token(
        *,
        refresh_token: str,
    ) -> dict[str,str]:
        
        serializer = JWTTokenRefreshSerializer(
            data={
                "refresh": refresh_token,
            }
        )
        
        try:
            serializer.is_valid(raise_exception=True)
        
        except TokenError:
            raise AuthenticationError(
                message="Invalid or expired refresh token."
            )
        
        data = serializer.validated_data
        
        return {
            "access_token": str(data["access"]),
            "refresh_token": str(
                data.get("refresh",refresh_token,)
            ),
            "token_type": "Bearer",
        }
        
    @staticmethod
    def logout(*,refresh_token: str) -> None:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        except TokenError:
            raise AuthenticationError(
                message="Invalid or expired refresh token."
            )
            
    @staticmethod
    def get_current_user(*,user):
        
        return user
    
    @staticmethod
    @transaction.atomic
    def change_password(
        *,
        user,
        current_password: str,
        new_password: str,
    ) -> None:
        if not user.check_password(current_password):
            raise AuthenticationError(
                message="Current password is incorrect."
            )
        
        user.set_password(new_password)
        user.save(
            update_fields=["password","updated_at",],
        )
        
