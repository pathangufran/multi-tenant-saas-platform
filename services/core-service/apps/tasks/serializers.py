from rest_framework.validators import ValidationError
from rest_framework import serializers
from .models import Task

class TaskCreateSerializer(serializers.Serializer):
    title = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    priority = serializers.ChoiceField(
        choices=Task.Priority.choices,
        required=False,
        default=Task.Priority.MEDIUM,
    )
    assignee_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    due_date = serializers.DateField(
        required=False,
        allow_null=True,
    )
    
    def validate_title(self,value):
        value = value.strip()
        
        if not value:
            raise ValidationError(
                "Task title cannot be empty."
            )
            
        return value
    
class TaskUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(
        max_length=255,
        trim_whitespace=True,
        required=False,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    priority = serializers.ChoiceField(
        choices=Task.Priority.choices,
        required=False,
    )
    status = serializers.ChoiceField(
        choices=Task.Status.choices,
        required=False,
    )
    assignee_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )
    due_date = serializers.DateField(
        required=False,
        allow_null=True,
    )
    
    def validate_title(self,value):
        value = value.strip()
        
        if not value:
            raise ValidationError(
                "Task title cannot be empty."
            )
            
        return value
    
class TaskResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    tenant_id = serializers.UUIDField()
    project_id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    priority = serializers.CharField()
    status = serializers.CharField()
    assignee_id = serializers.UUIDField()
    due_date = serializers.DateField()
    created_by = serializers.DateField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    
    