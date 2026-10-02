from rest_framework.validators import ValidationError
from rest_framework import serializers

class AttachmentCreateSerializer(serializers.Serializer):
    s3_key = serializers.CharField(max_length=1024,)
    filename = serializers.CharField(max_length=255,)
    content_type = serializers.CharField(max_length=255,)
    size = serializers.IntegerField(min_value=1,)
    
    def validate_s3_key(self, value):
        value = value.strip()

        if not value:
            raise ValidationError(
                "S3 key cannot be empty."
            )

        return value

    def validate_filename(self, value):
        value = value.strip()

        if not value:
            raise ValidationError(
                "Filename cannot be empty."
            )

        return value

    def validate_content_type(self, value):
        value = value.strip()

        if not value:
            raise ValidationError(
                "Content type cannot be empty."
            )

        return value

class AttachmentResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    task_id = serializers.UUIDField()
    s3_key = serializers.CharField()
    filename = serializers.CharField()
    content_type = serializers.CharField()
    size = serializers.IntegerField()
    created_by = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()