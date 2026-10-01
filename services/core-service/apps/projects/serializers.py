from rest_framework.validators import ValidationError
from rest_framework import serializers
from .models import Project

class ProjectCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    
    def validate_name(self,value):
        value = value.strip()
        
        if not value:
            raise ValidationError(
                "Project name cannot be empty."
            )
            
        return value
    
class ProjectUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=255,
        required=False,
        trim_whitespace=True,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    status = serializers.ChoiceField(
        choices=Project.Status.choices,
        required=False,
    )
    
    def validate_name(self,value):
        value = value.strip()
        
        if not value:
            raise ValidationError(
               "Project name cannot be empty." 
            )
            
        return value
    
class ProjectResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    tenant_id = serializers.UUIDField()
    name = serializers.CharField()
    description = serializers.CharField()
    status = serializers.CharField()
    created_by = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    
    