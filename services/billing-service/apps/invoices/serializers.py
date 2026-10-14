from decimal import Decimal
from rest_framework import serializers
from .models import Invoice

class InvoiceGenerateSerializer(
    serializers.Serializer,
):
    subscription_id = serializers.UUIDField()
    tax_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        default=Decimal("0.00"),
    )
    due_days = serializers.IntegerField(
        min_value=0,
        max_value=365,
        default=7,
    )
    
class InvoiceListQuerySerializer(
    serializers.Serializer,
):
    tenant_id = serializers.UUIDField()
    status = serializers.ChoiceField(
        choices=Invoice.Status.choices,
        default=False,
    )
    
class InvoiceLineItemSerializer(
    serializers.Serializer,
):
    id = serializers.UUIDField()
    invoice = serializers.UUIDField()
    description = serializers.CharField()
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField()
    amount = serializers.DecimalField()
    created_at = serializers.DateTimeField()
    
class InvoiceResponseSerializer(
    serializers.Serializer,
):  
    line_items = InvoiceLineItemSerializer(
        many=True,
        read_only=True,
    )
    id = serializers.UUIDField()
    invoice_number = serializers.CharField()
    tenant_id = serializers.UUIDField()
    subscription_id = serializers.UUIDField()
    plan_code = serializers.CharField()
    plan_name = serializers.CharField()
    currency = serializers.CharField()
    billing_interval = serializers.CharField()
    period_start = serializers.DateTimeField()
    period_end = serializers.DateTimeField()
    subtotal = serializers.DecimalField()
    tax_amount = serializers.DecimalField()
    total = serializers.DecimalField()
    status = serializers.CharField()
    issued_at = serializers.DateTimeField()
    due_at = serializers.DateTimeField()
    paid_at = serializers.DateTimeField()
    voided_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()