from rest_framework.validators import ValidationError
from rest_framework import serializers
from .models import Feature,PlanFeature

class FeatureCreateSerializer(serializers.Serializer):
    key = serializers.CharField(
        required=True,
    )
    name = serializers.CharField(
        required=True,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    value_type = serializers.ChoiceField(
        choices=Feature.ValueType.choices
    )
    is_active = serializers.BooleanField(
        required=False,
    )
    
    def validate_key(self,value):
        value = value.strip().lower()
        
        if not value.replace("_", "").replace("-", "").isalnum():
            raise serializers.ValidationError(
                "Feature keys may contain letters, numbers, \
                underscores, and hyphens."
            )
            
        queryset = Feature.objects.filter(key=value)
        if self.instance is not None:
            queryset = queryset.filter(pk=self.instance.pk)
            
        if queryset.exists():
            raise ValidationError(
                "A feature with this key already exists."
            )
            
        return value
    
class FeatureUpdateSerializer(serializers.Serializer):
    key = serializers.CharField(
        required=True,
    )
    name = serializers.CharField(
        required=True,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    value_type = serializers.ChoiceField(
        choices=Feature.ValueType.choices
    )
    is_active = serializers.BooleanField(
        required=False,
    )
    
class FeatureResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    key = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    value_type = serializers.CharField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    
class PlanFeatureCreateSerializer(
    serializers.Serializer,
):
    plan_id = serializers.UUIDField()
    feature_id = serializers.UUIDField()
    enabled = serializers.BooleanField(
        required=False,
    )
    valu = serializers.JSONField(
        required=False,
    )
    
    def validate(self,attrs):
        enabled = attrs.get(
            "enabled",
            self.instance.enabled if self.instance else True,
        )
        value = attrs.get(
            "value",
            self.instance.value if self.instance else None,
        )
        if not enabled and value is not None:
            raise ValidationError(
                {"value": "Disabled features must not have a value."}
            )
            
        feature_id = attrs.get(
            "feature_id",
            self.instance.feature_id if self.instance else None,
        )
        if feature_id is not None and value is not None:
            feature = Feature.objects.get(id=feature_id)
            
            if feature is None:
                raise ValidationError(
                    {"feature_id": "Feature not found."}
                )
                
            self._validate_value_type(feature,value)
            
        return attrs
    
    @staticmethod
    def _validate_value_type(feature, value):
        if feature.value_type == Feature.ValueType.BOOLEAN:
            if not isinstance(value, bool):
                raise serializers.ValidationError(
                    {"value": "This feature requires a boolean value."}
                )

        elif feature.value_type in (
            Feature.ValueType.INTEGER,
            Feature.ValueType.STORAGE_BYTES,
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise serializers.ValidationError(
                    {"value": "This feature requires an integer value."}
                )
            if value < 0:
                raise serializers.ValidationError(
                    {"value": "Feature values cannot be negative."}
                )
                
class PlanFeatureUpdateSerializer(
    serializers.Serializer,
):
    plan_id = serializers.UUIDField()
    feature_id = serializers.UUIDField()
    enabled = serializers.BooleanField(
        required=False,
    )
    valu = serializers.JSONField(
        required=False,
    )
                
class PlanFeatureResponseSerializer(
    serializers.Serializer,
):
    id = serializers.UUIDField()
    plan_id = serializers.UUIDField()
    feature_id = serializers.UUIDField()
    enabled = serializers.BooleanField()
    value = serializers.JSONField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    
class LimitCheckSerializer(serializers.Serializer):
    tenant_id = serializers.UUIDField()
    feature_key = serializers.CharField(
        max_length=100,
    )
    requested_quantity = serializers.IntegerField(
        min_value=1,
        default=1,
    )
    
    def validate_feature_key(self, value):
        return value.strip().lower()
    
class TenantEntitlementsSerializer(serializers.Serializer):
    tenant_id = serializers.UUIDField()
    has_subscription = serializers.BooleanField()
    plan = serializers.DictField(
        allow_null=True,
    )
    features = serializers.DictField()

class LimitCheckResultSerializer(serializers.Serializer):
    allowed = serializers.BooleanField()
    reason = serializers.CharField()
    feature_key = serializers.CharField()
    limit = serializers.IntegerField(
        allow_null=True,
    )
    current_usage = serializers.IntegerField(
        allow_null=True,
    )
    requested_quantity = serializers.IntegerField()
    remaining = serializers.IntegerField(
        required=False,
        min_value=0,
    )
    