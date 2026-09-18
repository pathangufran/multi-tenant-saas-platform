from rest_framework_simplejwt.authentication import (
    JWTAuthentication,
)

class TenantJWTAuthentication(JWTAuthentication):
    
    def authenticate(self,request):
        result = super().authenticate(request)
        
        if result is None:
            return None
        
        user, token = result
        
        request.authenticated_user_id = (
            token.get("user_id") or str(user.id)
        )
        
        return result