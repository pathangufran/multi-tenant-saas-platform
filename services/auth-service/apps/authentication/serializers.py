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
    
class CurrentUserSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    is_active = serializers.BooleanField()
    date_joined = serializers.DateTimeField()
    
class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        trim_whitespace=False,
    )
    
    def validate_current_password(self,value):
        if not value:
            raise ValidationError(
                "Current password is required."
            )
            
        return value
    
    def validate_new_password(self,value):
        if not value:
            return ValidationError(
                "New password is required."
            )
        if value != value.strip():
            raise ValidationError(
                "New password cannot start or \
                end with whitespace."
            )
            
        return value
    
    def validate(self,attrs):
        if attrs["current_password"] == attrs["new_password"]:
            raise ValidationError(
                {
                    "new_password": (
                        "New password must be different "
                        "from the current password."
                    )
                }
            )
            
        return attrs

class PasswordChangeResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    
class EmailVerificationSendSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self,value):
        try:
            validate_email(value)
        
        except ValidationError:
            raise ValidationError(
                "Please enter a valid email."
            )
            
        return value.lower().strip()
    
class EmailVerificationVerifySerializer(serializers.Serializer):
    token = serializers.UUIDField()
    
class EmailVerificationResponseSerializer(serializers.Serializer):
    message = serializers.CharField()