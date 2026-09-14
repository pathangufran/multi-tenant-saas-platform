from rest_framework import serializers
from django.core.validators import validate_email
from rest_framework.validators import ValidationError

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_email(self,value):
        try:
            validate_email(value)

        except ValidationError:
            raise ValidationError(
                "Please enter a valid email."
            )
            
        return value

    def validate_password(self,value):
        if len(value) < 8:
            raise ValidationError(
                "Password should minimum 8 characters."
            )
        
        if not value:
            raise ValidationError(
                "Password is required."
            )   

        return value 
    
class LoginResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField()
    
class TokenRefreshSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(
        write_only=True,
    )
    
class TokenRefreshResponseSerializer(serializers.Serializer):
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    token_type = serializers.CharField()
    
class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(
        write_only=True,
    )

class LogoutResponseSerializer(serializers.Serializer):
    message = serializers.CharField()