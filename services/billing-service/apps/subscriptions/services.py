import calendar
from uuid import UUID 
from datetime import datetime
from django.utils import timezone
from .models import Subscription
from apps.plans.models import Plan
from django.db import transaction,IntegrityError

OPEN_STATUSES = {
    Subscription.Status.TRIALING,
    Subscription.Status.ACTIVE,
    Subscription.Status.PAST_DUE,
}

def add_billing_interval(
    value: datetime,
    interval: str,
) -> datetime:
    
    """Add one calendar month or year, 
    clamping the day to the target month."""

    if interval == Plan.BillingInterval.MONTHLY:
        year = value.year + value.month // 12
        month = value.month % 12 + 1
    elif interval == Plan.BillingInterval.YEARLY:
        year = value.year + 1
        month = value.month
    else:
        raise ValueError(
            "Unsupported billing interval."
        )
        
    day = min(value.day,calendar.monthrange(year,month)[1])
    return value.replace(year=year,month=month,day=day)

class SubscriptionService:
    
    @staticmethod
    def list_subscriptions(
        *,
        tenant_id: UUID
    ) -> Subscription:
        
        return (
            Subscription.objects
            .select_related("plan")
            .filter(tenant_id=tenant_id)
        )
        
    @staticmethod
    def get_subscription(
        *,
        subscription_id: UUID,
    ) -> Subscription:
        
        return (
            Subscription.objects
            .select_related("plan")
            .get(id=subscription_id)
        )
        
    @staticmethod
    def get_open_subscription(
        *,
        tenant_id: UUID,
    ) -> Subscription:
        
        return (
            Subscription.objects
            .select_related("plan")
            .get(
                tenant_id=tenant_id,
                status__in=OPEN_STATUSES,
            )
        )
        
    @staticmethod
    @transaction.atomic
    def create_subscription(
        *,
        data: dict,
    ) -> Subscription:
        
        plan = Plan.objects.get(
            plan_id=data["plan_id"],
            is_active=True,
        )
        
        if plan is None:
            raise ValueError(
                "The selected plan does not \
                exist or is inactive."
            )
        
        if Subscription.objects.filter(
            tenant_id=data["tenant_id"],
            status__in=OPEN_STATUSES,
        ).exists():
            raise ValueError(
                "This tenant already has an \
                open subscription."
            )
            
        start_at = data.get("start_at",timezone.now())
        period_end = add_billing_interval(
            start_at,
            plan.billing_interval,
        )
        
        try:
            with transaction.atomic():
                return Subscription.objects.create(
                    tenant_id=data["tenant_id"],
                    plan=plan,
                    status=Subscription.status.ACTIVE,
                    start_at=start_at,
                    current_period_start=start_at,
                    current_period_end=period_end,
                )
                
        except IntegrityError:
            raise ValueError(
                "The subscription conflicts with \
                an existing record. "
                "The tenant may already have an \
                open subscription."
            )
            
    @staticmethod
    @transaction.atomic
    def cancel_subscription(
        *,
        subscription_id: UUID,
        at_period_end=True,
    ) -> Subscription:
        
        subcription = (
            Subscription.objects
            .select_for_update()
            .get(id=subscription_id)
        )
        
        if subcription is None:
            raise ValueError(
                "Subscription not found."
            )
            
        if subcription.status in (
            Subscription.Status.CANCELED,
            Subscription.Status.EXPIRED,
        ):
            return subcription
        
        if at_period_end:
            subcription.cancel_at_period_end = True
            subcription.save(
                update_fields=[
                    "cancel_at_period_end",
                    "updated_at",
                ]
            )
            
            return subcription
        
        subcription.status = Subscription.Status.CANCELED
        subcription.cancel_at_period_end = False
        subcription.canceled_at = timezone.now()
        subcription.ended_at = timezone.now()
        subcription.save(
            update_fields=[
                "status",
                "cancel_at_period_end",
                "canceled_at",
                "ended_at",
            ]
        )
        
        return subcription
    
    @staticmethod
    @transaction.atomic
    def renew_subscription(
        *,
        subscription_id: UUID,
    ) -> Subscription:
        
        subscription = (
            Subscription.objects
            .select_for_update()
            .select_related("plan")
            .get(id=subscription_id)
        )
        
        if subscription is None:
            raise ValueError(
                "Subscription not found."
            )
            
        if subscription.status not in (
            Subscription.Status.ACTIVE,
            Subscription.Status.PAST_DUE,
        ):
            raise ValueError(
                "Only active or past-due \
                subscriptions can be renewed."
            )
            
        if subscription.cancel_at_period_end:
            raise ValueError(
                "A subscription scheduled for \
                cancellation cannot be renewed."
            )
            
        new_period_start = max(
            subscription.current_period_end,
            timezone.now(),
        )
        new_period_end = add_billing_interval(
            new_period_start,
            subscription.plan.billing_interval,
        )
        
        subscription.current_period_start = new_period_start
        subscription.current_period_end = new_period_end
        subscription.status = Subscription.Status.ACTIVE
        subscription.save(
            update_fields=[
                "current_period_start",
                "current_period_end",
                "status",
                "updated_at",
            ]
        )

        return subscription
    
    @staticmethod
    def finalize_period_end(
        *,
        subscription_id: UUID,
    ) -> Subscription:
        
        subscription = (
            Subscription.objects
            .select_for_update()
            .get(id=subscription_id)
        )
        
        if subscription is None:
            raise ValueError(
                "Subscription not found."
            )
            
        if subscription.status not in OPEN_STATUSES:
            return subscription
        
        if (
            subscription.current_period_end 
            >
            timezone.now()
        ):
            raise ValueError(
                "The current billing period has not ended."
            )
            
        if subscription.cancel_at_period_end:
            subscription.status = Subscription.Status.CANCELED
            subscription.cancel_at_period_end = False
            subscription.canceled_at = timezone.now()
            subscription.ended_at = timezone.now()
            subscription.save(
                update_fields=[
                    "status",
                    "cancel_at_period_end",
                    "canceled_at",
                    "ended_at",
                    "updated_at",
                ]
            )
            return subscription
        
        subscription.status = Subscription.Status.EXPIRED
        subscription.ended_at = timezone.now()
        subscription.save(
            update_fields=[
                "status","ended_at","updated_at"
            ]
        )

        return subscription