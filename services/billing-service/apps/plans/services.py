from uuid import UUID
from django.db import (
    IntegrityError,
    transaction,
)
from apps.plans.models import Plan

class PlanService:
    
    @staticmethod
    @transaction.atomic
    def create_plan(
        *,
        data: dict,
    ) -> Plan:
        
        try:
            with transaction.atomic():
                plan = Plan.objects.create(**data,)
                
        except IntegrityError as exc:
            raise ValueError(
                "The plan conflicts with an \
                existing database record."
            ) from exc
            
        return plan
            
    @staticmethod
    def list_plans(*,public_only=True):
        
        plans = Plan.objects.all()
        
        if public_only:
            plans = plans.filter(
                is_active=True,
                is_public=True,
            )
            
        return plans.order_by("price","name")
        
    @staticmethod
    @transaction.atomic
    def update_plan(
        *,
        plan_id: UUID,
        data: dict,   
    ) -> Plan:
        
        try:
            plan = (
                Plan.objects
                .select_for_update()
                .get(id=plan_id)
            )
            
        except Plan.DoesNotExist:
            raise ValueError(
                "Plan not found."
            )
            
        if (
            "code" in data 
            and data["code"] != plan.code
        ):
            raise ValueError(
                "Plan code cannot be changed \
                after creation."
            )
            
        for field,value in data.items():
            setattr(plan,field,value)
            
        try:
            with transaction.atomic():
                plan.save()
                
        except IntegrityError:
            raise ValueError(
                "The plan update conflicts \
                with an existing record."
            )
        
        return plan 
        
    @staticmethod
    @transaction.atomic
    def delete_plan(*,plan_id: UUID) -> None:
        
        try:
            plan = (
                Plan.objects
                .select_for_update()
                .get(id=plan_id)
            )
            
        except Plan.DoesNotExist:
            raise ValueError(
                "Plan not found."
            )
            
        if plan.is_active:
            plan.is_active = False
            
        with transaction.atomic():
            plan.save(
                update_fields=[
                    "is_active","updated_at"
                ]
            )
        
        return plan
    
    @staticmethod
    def get_plan_by_code(
        *,
        code: str,
        public_only=True,
    ) -> Plan:
        
        plan = Plan.objects.filter(code=code)
        
        if public_only:
            plan = plan.get(
                is_active=True,
                is_public=True,
            )
            
        return plan
    
    @staticmethod
    def get_plan_by_id(
        *,
        plan_id: UUID
    ) -> Plan:
        
        try:
            plan = Plan.objects.get(id=plan_id)
            
        except Plan.DoesNotExist:
            raise ValueError(
                "Plan not found."
            )
            
        return plan