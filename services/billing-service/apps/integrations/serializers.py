from rest_framework import serializers

class BillingEventSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    event_type = serializers.CharField()
    aggregate_type = serializers.CharField()
    aggregate_id = serializers.CharField()
    tenant_id = serializers.UUIDField()
    payload = serializers.JSONField()
    status = serializers.CharField()
    attempts = serializers.IntegerField()
    last_error = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

class BillingEventDeliverySerializer(serializers.ModelSerializer):
    id = serializers.UUIDField()
    event_id = serializers.UUIDField()
    destination = serializers.CharField()
    status = serializers.CharField()
    attempts = serializers.IntegerField()
    last_error = serializers.CharField()
    delivered_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()