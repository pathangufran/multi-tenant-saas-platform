from .models import Tenant
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
    
class TenantResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()