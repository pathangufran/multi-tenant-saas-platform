from .models import Tenant,Permission
from rest_framework import serializers
from rest_framework.validators import ValidationError

class TenantCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    slug = serializers.CharField(max_length=100)
    
    def validate_name(self,value):
        value = value.strip()
        
        if not value:
            raise ValidationError(
                "Tenant name is required."
            )
        
        return value
    
    def validate_slug(self,value):
        value = value.lower().strip()
        
        if not value:
            raise ValidationError(
                "Tenant slug is required."
            )
            
        return value
    
class TenantUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=255,
        required=False,
    )
    slug = serializers.CharField(
        max_length=100,
        required=False,
    )
    
    def validate_name(self,value):
        value = value.strip()
        
        if not value:
            raise ValidationError(
                "Tenant name cannot be empty."
            )
            
        return value
    
    def validate_slug(self,value):
        value = value.strip().lower()
        
        if not value:
            raise ValidationError(
                "Tenant slug cannot be empty."
            )
            
        return value
    
class TenantResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    
class PermissionAssignmentSerializer(
    serializers.Serializer
):
    permission_code = serializers.CharField(
        max_length=100,
        trim_whitespace=True,
    )
    
class PermissionReplaceSerializer(
    serializers.Serializer
):
    permission_codes = serializers.ListField(
        child=serializers.CharField(
            max_length=100,
            trim_whitespace=True,
        ),
        allow_empty=True,
    )
    
    def validate_permission_codes(self,value):
        normalized = []
        
        for code in value:
            code = code.strip()
            
            if not code:
                raise ValidationError(
                    "Permission codes cannot be empty."
                )
            
            normalized.append(code)
            
        if len(normalized) != len(set(normalized)):
            raise ValidationError(
                "Permission codes must be unique."
            )
            
        return normalized
    
class PermissionResponseSerializer(
    serializers.Serializer
):
    id = serializers.UUIDField()
    code = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()