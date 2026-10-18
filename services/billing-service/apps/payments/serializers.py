from rest_framework.validators import ValidationError
from rest_framework import serializers
from apps.payments.models import Payment

class PaymentCreateSerializer(
    serializers.Serializer,
):
    invoice_id = serializers.UUIDField()
    idempotency_key = serializers.CharField(
        max_length=128,
        trim_whitespace=True,
    )
    provider = serializers.ChoiceField(
        choices=Payment.Provider.choices,
        default=Payment.Provider.MOCK,
    )
    
    def validate_idempotency_key(self,value):
        value = value.strip()
        
        if not value:
            raise ValueError(
                "Idempotency key cannot be blank."
            )
            
        return value
    
class PaymentListQuerySerializer(
    serializers.Serializer,
):
    invoice_id = serializers.UUIDField(
        required=False,
    )
    tenant_id = serializers.UUIDField(
        required=False,
    )
    status = serializers.ChoiceField(
        choices=Payment.Status.choices,
        required=False,
    )
    
class PaymentResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    invoice_id = serializers.UUIDField()
    invoice_number = serializers.CharField()
    tenant_id = serializers.UUIDField()
    provider = serializers.CharField()
    provider_payment_id = serializers.CharField()
    idempotency_key = serializers.CharField()
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    currency = serializers.CharField()
    status = serializers.CharField()
    checkout_url = serializers.URLField()
    failure_reason = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField()
    
class WebhookDataSerializer(serializers.Serializer):
    provider_payment_id = serializers.CharField(
        max_length=255,
    )
    status = serializers.ChoiceField(
        choices=[
            Payment.Status.SUCCEEDED,
            Payment.Status.FAILED,
            Payment.Status.CANCELED,
            Payment.Status.REFUNDED,
        ]
    )
    
class PaymentWebhookSerializer(
    serializers.Serializer,
):
    id = serializers.CharField(
        max_length=255,
    )
    type = serializers.ChoiceField(
        choices=[
            "payment.succeeded",
            "payment.failed",
            "payment.canceled",
            "payment.refunded",
        ]
    )
    data = WebhookDataSerializer()
    
    def validate(self,attrs):
        event_to_status = {
            "payment.succeeded": Payment.Status.SUCCEEDED,
            "payment.failed": Payment.Status.FAILED,
            "payment.canceled": Payment.Status.CANCELED,
            "payment.refunded": Payment.Status.REFUNDED,
        }
        
        expected_status = event_to_status[attrs["type"]]
        if attrs["data"]["status"] != expected_status:
            raise ValidationError(
                "Status does not match the webhook event type."
            )
            
        return attrs
    
class WebhookEventSerializer(
    serializers.Serializer,
):
    id = serializers.UUIDField()
    provider = serializers.CharField()
    event_id = serializers.CharField()
    event_type = serializers.CharField()
    payload = serializers.JSONField()
    status = serializers.CharField()
    error_message = serializers.CharField()
    received_at = serializers.DateTimeField()
    processed_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()