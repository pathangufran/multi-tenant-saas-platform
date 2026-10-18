import requests
from uuid import UUID
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .clients import (
    IntegrationError,
    TenantServiceClient,
)
from .models import (
    BillingEvent,
    BillingEventDelivery,
)
from apps.subscriptions.services import (
    SubscriptionService,
)
from apps.subscriptions.models import (
    Subscription
)
from rest_framework.exceptions import NotFound

class BillingIntegrationService:
    DESTINATIONS = ("CORE", "NOTIFICATION")
    
    @classmethod
    def create_subscription(
        cls,
        data: dict
    ) -> Subscription:
        
        TenantServiceClient.validate_tenant(
            data["tenant_id"]
        )
        
        with transaction.atomic():
            subscription = (
                SubscriptionService.create_subscription(
                    data,
                )
            )
            
            event = cls.create_event(
                event_type="billing.subscription.created",
                aggregate_type="subscription",
                aggregate_id=str(subscription.id),
                tenant_id=subscription.tenant_id,
                payload={
                    "subscription_id": str(subscription.id),
                    "tenant_id": str(subscription.tenant_id),
                    "plan_id": str(subscription.plan_id),
                    "status": subscription.status,
                    "current_period_start": (
                        subscription.current_period_start
                        .isoformat()
                    ),
                    "current_period_end": (
                        subscription.current_period_end
                        .isoformat()
                    ),
                },
            )
            
            transaction.on_commit(
                lambda event_id=str(event.id): (
                    cls._enqueue_dispatch(event_id)
                )
            )

        return subscription
    
    @staticmethod
    def create_event(
        *,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        tenant_id: UUID,
        payload: dict,
    ) -> BillingEvent:
        
        event = BillingEvent.objects.create(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            tenant_id=tenant_id,
            payload=payload,
        )

        BillingEventDelivery.objects.bulk_create([
            BillingEventDelivery(
                event=event,
                destination=destination,
            )
            for destination in BillingIntegrationService.DESTINATIONS
        ])

        return event
    
    @staticmethod
    def list_events(
        *,
        status=None,
        tenant_id=None,
    ) -> BillingEvent:
        
        queryset = (
            BillingEvent.objects.all()
            .prefetch_related("deliveries")
        )

        if status:
            queryset = queryset.filter(
                status=status
            )
        if tenant_id:
            queryset = queryset.filter(
                tenant_id=tenant_id
            )

        return queryset

    @staticmethod
    def get_event(event_id):

        try:
            return (
                BillingEvent.objects
                .prefetch_related("deliveries")
                .get(id=event_id)
            )
            
        except BillingEvent.DoesNotExist as exc:
            raise NotFound(
                "Billing event not found."
            ) from exc
    
    @staticmethod
    def _enqueue_dispatch(event_id: UUID):
        from .tasks import dispatch_billing_event
        
        try:
            dispatch_billing_event.delay(event_id)
        
        except Exception:
            pass
        
    @staticmethod
    def _destination_url(destination):
        base_urls = {
            "CORE": settings.CORE_SERVICE_URL,
            "NOTIFICATION": (
                settings.NOTIFICATION_SERVICE_URL,
            )
        }
        
        base_url = base_urls.get(destination)
        if not base_url:
            raise IntegrationError(
                f"Unknown event destination: {destination}"
            )
            
        return (
            f"{base_url.rstrip('/')}/api/internal/v1/events/"   
        )
        
    @classmethod
    def dispatch_event(cls,event_id: UUID):
        
        try:
            event = (
                BillingEvent.objects.get(id=event_id)
            )
        
        except BillingEvent.DoesNotExist:
            return {
                "status": "not_found",
                "event_id": str(event_id)
            }
            
        deliveries = (
            BillingEventDelivery.objects.filter(
                event=event
            ).exclude(
                status=BillingEventDelivery.Status.DELIVERED,
            )
        )
        
        for delivery in deliveries:
            
            if (
                delivery.next_attempt_at is not None
                and delivery.next_attempt_at > timezone.now()
            ):
                continue
            
            try:
                response = requests.post(
                    cls._destination_url(delivery.destination),
                    json={
                        "event_id": str(event.id),
                        "event_type": event.event_type,
                        "aggregate_type": event.aggregate_type,
                        "aggregate_id": event.aggregate_id,
                        "tenant_id": str(event.tenant_id),
                        "occurred_at": event.created_at.isoformat(),
                        "data": event.payload,
                    },
                    headers={
                        "X-Internal-Service-Key": (
                            settings.INTERNAL_SERVICE_KEY
                        ),
                        "Content-Type": "application/json",
                    },
                    timeout=settings.INTEGRATION_TIMEOUT_SECONDS,
                )
                
                if response.status_code in (200,201,202,204):
                    delivery.status = (
                        BillingEventDelivery.Status.DELIVERED,
                    )
                    delivery.delivered_at = timezone.now()
                    delivery.last_error = ""
                    delivery.next_attempt_at = None
                else:
                    delivery.status = (
                        BillingEventDelivery.Status.FAILED
                    )
                    delivery.last_error = (
                        f"HTTP {response.status_code}: "
                        f"{response.text[:350]}"
                    )
                    delivery.next_attempt_at = cls._next_retry(
                        delivery.attempts
                    )

            except requests.RequestException as exc:
                delivery.status = BillingEventDelivery.Status.FAILED
                delivery.last_error = str(exc)[:500]
                delivery.next_attempt_at = cls._next_retry(
                    delivery.attempts
                )

            delivery.attempts += 1
            delivery.save(
                update_fields=[
                    "status",
                    "attempts",
                    "last_error",
                    "next_attempt_at",
                    "delivered_at",
                    "updated_at",
                ]
            )
            
        cls._refresh_event_status(event)
        event.refresh_from_db()
        
        return {
            "status": event.status,
            "event_id": str(event.id),
        }
        
    @staticmethod
    def _next_retry(attempts):
        
        delay_seconds = min(
            30 * (2 ** min(attempts, 7)),
            3600
        )
        return (
            timezone.now() +
            timedelta(seconds=delay_seconds)
        )
        
    @staticmethod
    def _refresh_event_status(event):
        deliveries = list(event.deliveries.all())

        if deliveries and all(
            item.status == (
                BillingEventDelivery.Status.DELIVERED
            )
            for item in deliveries
        ):
            event.status = BillingEvent.Status.DELIVERED
            event.last_error = ""
        elif any(
            item.status == (
                BillingEventDelivery.Status.FAILED
            )
            for item in deliveries
        ):
            event.status = BillingEvent.Status.FAILED
            event.last_error = "; ".join(
                f"{item.destination}: {item.last_error}"
                for item in deliveries
                if item.status == (
                    BillingEventDelivery.Status.FAILED
                )
            )[:500]
        else:
            event.status = BillingEvent.Status.PENDING

        event.attempts = sum(
            item.attempts for item in deliveries
        )
        event.save(
            update_fields=[
                "status",
                "last_error",
                "attempts",
                "updated_at",
            ]
        )
        
    @classmethod
    def retry_event(cls,event_id: UUID):
        try:
            event = BillingEvent.objects.get(
                id=event_id,
            )
        
        except BillingEvent.DoesNotExist:
            return {
                "status": "not_found",
                "event_id": str(event_id),
            }
            
        event.deliveries.exclude(
            status=(
                BillingEventDelivery.Status.DELIVERED,
            )
        ).update(
            status=(
                BillingEventDelivery.Status.PENDING,
            ),
            next_attempt_at=timezone.now(),
            last_error="",
        )

        event.status = BillingEvent.Status.PENDING
        event.last_error = ""
        event.save(
            update_fields=[
                "status","last_error","updated_at"
            ]
        )

        return cls.dispatch_event(event.id)
    
    @classmethod
    def dispatch_pending_events(cls,limit=100):
        event_ids = (
            BillingEvent.objects.filter(
                deliveries__status__in=[
                    BillingEventDelivery.Status.PENDING,
                    BillingEventDelivery.Status.FAILED,
                ],
            )
            .filter(
                deliveries__next_attempt_at__isnull=True
            )
            .values_list("id", flat=True)
            .distinct()[:limit]
        )

        due_ids = (
            BillingEvent.objects.filter(
                deliveries__status=(
                    BillingEventDelivery.Status.FAILED,
                ),
                deliveries__next_attempt_at__lte=timezone.now(),
            )
            .values_list("id", flat=True)
            .distinct()[:limit]
        )
        
        ids = list(
            dict.fromkeys([*event_ids, *due_ids])
        )[:limit]

        return [
            cls.dispatch_event(event_id)
            for event_id in ids
        ]
