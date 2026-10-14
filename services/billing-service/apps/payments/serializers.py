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
    amount = serializers.DecimalField()
    currency = serializers.CharField()
    status = serializers.CharField()
    checkout_url = serializers.URLField()
    failure_reason = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField()