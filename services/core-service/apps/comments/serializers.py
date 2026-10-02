from rest_framework.validators import ValidationError
from rest_framework import serializers
from .models import Comment

class CommentCreateSerializer(serializers.Serializer):
    content = serializers.CharField(
        max_length=5000,
    )
    
    def validate_content(self,value):
        value = value.strip()
        
        if not value:
            raise ValidationError(
                "Comment content cannot be empty."
            )
            
        return value
    
class CommentUpdateSerializer(serializers.Serializer):
    content = serializers.CharField(
        max_length=5000,
        required=True,
    )
    
    def validate_content(self,value):
        value = value.strip()
        
        if not value:
            raise ValidationError(
                "Comment content cannot be empty."
            )
            
        return value
    
class CommentResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    task_id = serializers.UUIDField()
    content = serializers.CharField()
    created_by = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()