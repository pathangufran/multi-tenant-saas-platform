from apps.users.models import User
from rest_framework_simplejwt.tokens import RefreshToken
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
        