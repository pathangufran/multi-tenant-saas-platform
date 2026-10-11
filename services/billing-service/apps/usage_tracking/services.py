from uuid import UUID
from django.db import transaction
from .models import UsageRecord

class UsageService:
    
    @staticmethod
    def list_usage(
        *,
        tenant_id: UUID,   
    ) -> UsageRecord:
        
        return UsageRecord.objects.filter(
            tenant_id=tenant_id
        ).order_by("-created_at")
        
    @staticmethod
    def get_usage(
        *,
        tenant_id: UUID,
        metric: str,
    ) -> UsageRecord:
        
        return UsageRecord.objects.get(
            tenant_id=tenant_id,
            metric=metric,
        )
        
    @staticmethod
    @transaction.atomic
    def set_usage(
        *,
        tenant_id: UUID,
        metric: str,
        quantity: int,
        source : str = "manual",
    ) -> UsageRecord:
        
        if quantity < 0:
            raise ValueError(
                "Usage quantity cannot be negative."
            )
            
        if metric not in UsageRecord.Metric.values:
            raise ValueError(
                 "Unsupported usage metric."
            )
            
        record,_ = UsageRecord.objects.update_or_create(
            tenant_id=tenant_id,
            metric=metric,
            defaults={
                "quantity": quantity,
                "source": source,
            },
        )
        
        return record
    
    @staticmethod
    @transaction.atomic
    def adjust_usage(
        *,
        tenant_id: UUID,
        metric: str,
        delta: int,
        source: str = "manual",
    ) -> UsageRecord:
        
        if delta == 0:
            raise ValueError(
                "Delta must be non-zero."
            )
            
        if metric not in UsageRecord.Metric.values:
            raise ValueError(
                "Unsupported usage metric."
            )
            
        record,_ = UsageRecord.objects.get_or_create(
            tenant_id=tenant_id,
            metric=metric,
            defaults={
                "quantity": 0,
                "source": source,
            },
        )
        
        record = (
            record.objects
            .select_for_update()
            .get(pk=record.pk)
        )
        
        new_quantity = record.quantity + delta
        
        if new_quantity < 0:
            raise ValueError(
                "Adjustment would make usage negative. "
                f"Current usage is {record.quantity}."
            )
            
        record.quantity = new_quantity
        record.source = source
        record.save(
            update_fields=[
                "quantity","source","updated_at"
            ]
        )
        
        return record