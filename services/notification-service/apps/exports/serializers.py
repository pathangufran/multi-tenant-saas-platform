from rest_framework.validators import ValidationError
from rest_framework import serializers
from .models import Export

class ExportCreateSerializer(serializers.Serializer):
    export_type = serializers.ChoiceField(
        choices=Export.ExportType.choices,
    )
    
class ExportResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    tenant_id = serializers.UUIDField()
    requested_by = serializers.UUIDField()
    export_type = serializers.CharField()
    status = serializers.CharField()
    file_name = serializers.CharField()
    storage_key = serializers.CharField()
    row_count = serializers.IntegerField()
    error_message = serializers.CharField()
    created_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField()