import re
from rest_framework import serializers
from apps.plans.models import Plan
from rest_framework.validators import ValidationError

class PlanCreateSerializer(serializers.Serializer):
    code = serializers.CharField(required=True)
    name = serializers.CharField(required=True)
    description = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    price = serializers.DecimalField(
        required=True,
        max_digits=12,
        decimal_places=2,
    )
    currency = serializers.CharField(required=True)
    billing_interval = serializers.CharField(required=True)
    is_active = serializers.BooleanField(required=True)
    is_public = serializers.CharField(required=True)
    
    def validate_code(self,value):
        value = value.strip().upper()
        
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,49}", value):
            raise ValidationError(
                "Use 2–50 characters: start with a letter, \
                followed by "
                "uppercase letters, numbers, or underscores."
            )
            
        queryset = Plan.objects.filter(code=value)
        
        if self.instance is not None:
            queryset = queryset.exclude(
                pk=self.instance.pk,
            )
            
        if queryset.exists():
            raise ValidationError(
                "A plan with this code already exists."
            )
            
        if (
            self.instance is not None 
            and value != self.instance.code
        ):
            raise ValidationError(
                "Plan code cannot be changed after creation."
            )
            
        return value
    
    def validate_name(self,value):
        value = value.strip()
        
        if not value:
            raise ValidationError(
                "Plan name cannot be blank."
            )
            
        return value
    
    def validate_currency(self,value):
        value = value.strip().upper()
        
        if not re.fullmatch(r"[A-Z]{3}", value):
            raise ValidationError(
                "Currency must be a three-letter \
                ISO-style code."
            )
            
        return value
    
    def validate_price(self,value):
        
        if value < 0:
            raise ValidationError(
                "Price cannot be negative."
            )
            
        return value
    
    def validate_billing_interval(self, value):
        allowed = {
            choice[0] for choice in 
            Plan.BillingInterval.choices
        }

        if value not in allowed:
            raise serializers.ValidationError(
                "Billing interval must be MONTHLY \
                or YEARLY."
            )

        return value
    
class PlanResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    price = serializers.IntegerField()
    currency = serializers.CharField()
    billing_interval = serializers.CharField()
    is_active = serializers.BooleanField()
    is_public = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()