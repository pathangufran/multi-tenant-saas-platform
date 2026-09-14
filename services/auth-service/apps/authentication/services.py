from django.db import transaction
from apps.users.models import User
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import (
    TokenRefreshSerializer as JWTTokenRefreshSerializer
)
from apps.common.exceptions import AuthenticationError
from .models import AuthenticationAuditEvent
from .audit_service import (
    AuthenticationAuditService,
)

class AuthenticationService:
    
    @classmethod
    def authenticated_user(
        cls,
        *,
        email: str,
        password: str,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> User:
        
        try:
            user = User.objects.get(
                email__iexact=email,
            )
        except User.DoesNotExist:
            AuthenticationAuditService.record(
                event_type=(
                    AuthenticationAuditEvent
                    .EventType
                    .LOGIN_FAILURE
                ),
                ip_address=ip_address,
                request_id=request_id,
                metadata={
                    "reason": "invalid_credentials",
                },
            )

            raise AuthenticationError(
                message="Invalid email or password."
            )
            
        if not user.check_password(password):
            AuthenticationAuditService.record(
                event_type=(
                    AuthenticationAuditEvent
                    .EventType
                    .LOGIN_FAILURE
                ),
                user=user,
                ip_address=ip_address,
                request_id=request_id,
                metadata={
                    "reason": "invalid_credentials",
                },
            )
            
            raise AuthenticationError(
                message="Invalid email or password."
            )
            
        if not user.is_active:
            AuthenticationAuditService.record(
                event_type=(
                    AuthenticationAuditEvent
                    .EventType
                    .LOGIN_FAILURE
                ),
                user=user,
                ip_address=ip_address,
                request_id=request_id,
                metadata={
                    "reason": "inactive_account",
                },
            )
            
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
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> dict[str,str]:
        
        user = cls.authenticated_user(
            email=email,
            password=password,
            ip_address=ip_address,
            request_id=request_id,
        )
        AuthenticationAuditService.record(
            event_type= (
                AuthenticationAuditEvent
                .EventType
                .LOGIN_SUCCESS
            ),
            user=user,
            ip_address=ip_address,
            request_id=request_id,
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
    def logout(
        *,
        refresh_token: str,
        user=None,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> None:
        try:
            token = RefreshToken(refresh_token)
            
            if user is None:
                user_id = token.get("user_id")
                try:
                    user = User.objects.get(
                        id=user_id,
                    )
                except User.DoesNotExist:
                    user = None
                    
            token.blacklist()
        
        except TokenError:
            raise AuthenticationError(
                message="Invalid or expired refresh token."
            )
            
        AuthenticationAuditService.record(
            event_type=(
                AuthenticationAuditEvent
                .EventType
                .LOGOUT
            ),
            user=user,
            ip_address=ip_address,
            request_id=request_id,
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
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> None:
        if not user.check_password(current_password):
            raise AuthenticationError(
                message="Current password is incorrect."
            )
        
        user.set_password(new_password)
        user.save(
            update_fields=["password","updated_at",],
        )    
        AuthenticationAuditService.record(
            event_type=(
                AuthenticationAuditEvent
                .EventType
                .PASSWORD_CHANGED
            ),
            user=user,
            ip_address=ip_address,
            request_id=request_id,
        )
        
