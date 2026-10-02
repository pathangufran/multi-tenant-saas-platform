from rest_framework.validators import ValidationError
from rest_framework import serializers
from .models import Tag

class TagCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=100,
    )
    
    def validate_name(self,value):
        value = value.strip()
        
        if not value:
            raise ValidationError(
                "Tag name cannot be empty."
            )
            
        return value
    
class TagUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=100,
    )
    
    def validate_name(self,value):
        value = value.strip()
        
        if not value:
            raise ValidationError(
                "Tag name cannot be empty."
            )
            
        return value
    
class TagResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    created_by = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    
class TaskTagCreateSerializer(serializers.Serializer):
    tag_id = serializers.UUIDField()