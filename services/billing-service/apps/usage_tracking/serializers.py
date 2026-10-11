from rest_framework.validators import ValidationError
from rest_framework import serializers
from .models import UsageRecord

class UsageSetSerializer(serializers.Serializer):
    tenant_id = serializers.UUIDField()
    metric = serializers.ChoiceField(
        choices=UsageRecord.Metric.choices,
    )
    quantity = serializers.IntegerField(
        min_value=0,
    )
    source = serializers.CharField(
        max_length=64,
        required=False,
        default="manual",
    )

    def validate_source(self, value):
        value = value.strip()

        if not value:
            raise ValidationError(
                "Source cannot be blank."
            )

        return value

class UsageAdjustmentSerializer(serializers.Serializer):
    tenant_id = serializers.UUIDField()
    metric = serializers.ChoiceField(
        choices=UsageRecord.Metric.choices,
    )
    delta = serializers.IntegerField()
    source = serializers.CharField(
        max_length=64,
        required=False,
        default="manual",
    )

    def validate_delta(self, value):
        if value == 0:
            raise ValidationError(
                "Delta must be non-zero. Use usage \
                reporting to set an exact value."
            )

        return value

    def validate_source(self, value):
        value = value.strip()

        if not value:
            raise ValidationError(
                "Source cannot be blank."
            )

        return value

class UsageQuerySerializer(serializers.Serializer):
    tenant_id = serializers.UUIDField()

class UsageRecordSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    tenant_id = serializers.UUIDField()
    metric = serializers.CharField()
    quantity = serializers.IntegerField()
    source = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()