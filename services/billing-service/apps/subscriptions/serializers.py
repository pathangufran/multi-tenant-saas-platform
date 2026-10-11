from rest_framework import serializers
from apps.plans.models import Plan

class SubscriptionCreateSerializer(
    serializers.Serializer,
):
    tenant_id = serializers.UUIDField()
    plan_id = serializers.UUIDField()
    start_at = serializers.DateTimeField(
        required=False,
    )
    
class SubscriptionCancelSerializer(
    serializers.Serializer,
):
    at_period_at = serializers.BooleanField(
        default=True,
    )
    
class SubscriptionPlanSerializer(
    serializers.Serializer,
):
    plan_code = serializers.CharField(
        source=Plan.code, 
        read_only=True,
    )
    plan_name = serializers.CharField(
        source=Plan.name, 
        read_only=True,
    )
    
class SubscriptionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    tenant_id = serializers.UUIDField()
    plan_id = serializers.UUIDField()
    plan = SubscriptionPlanSerializer()
    status = serializers.CharField()
    start_at = serializers.DateTimeField()
    current_period_start = serializers.DateTimeField(),
    current_period_end = serializers.DateTimeField()
    cancel_at_period_end = serializers.BooleanField()
    canceled_at = serializers.DateTimeField()
    ended_at = serializers.DateTimeField()
    external_subscription_id = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()