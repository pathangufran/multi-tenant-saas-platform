from uuid import UUID
from django.db import transaction,IntegrityError
from django.utils import timezone
from apps.invoices.models import Invoice
from .models import Payment,WebhookEvent
from .providers import (
    PaymentProviderError,
    get_payment_provider,
    verify_payment_webhook_signature,
)


class PaymentService:
    
    @staticmethod
    def list_payments(
        *,
        invoice_id=None,
        tenant_id=None,
        status=None,
    ) -> Payment:
        
        payment = (
            Payment.objects.select_related("invoice")
        )
    
        if invoice_id is not None:
            payment = payment.filter(
                invoice_id=invoice_id,
            )
        if tenant_id is not None:
            payment = payment.filter(
                invoice__tenant_id=tenant_id,
            )
        if status is not None:
            payment = payment.filter(
                status=status,
            )
            
        return payment
            
    @staticmethod
    def get_payment(
        *,
        payment_id: UUID,
    ) -> Payment:
        try:
            payment = (
                Payment.objects
                .select_related("invoice")
                .get(id=payment_id)
            )
        
        except Payment.DoesNotExist:
            raise ValueError(
                "Payment not found."
            )
            
    @staticmethod
    def _get_existing_idempotent_payment(
        *,
        idempotency_key: str,
        invoice_id: UUID,
        provider: str,
    ) -> Payment:
        try:
            existing = (
                Payment.objects
                .select_related("invoice")
                .get(
                    idempotency_key=idempotency_key,
                )
            )
            
        except Payment.DoesNotExist:
            return None
        
        if (
            str(existing.invoice_id) != str(invoice_id)
            or existing.provider != provider
        ):
            raise ValueError(
                "This key has already been used with "
                "a different invoice or provider."
            )

        return existing
        
    @classmethod
    def create_payment(
        cls,
        *,
        invoice_id: UUID,
        idempotency_key: str,
        provider=Payment.Provider.MOCK,
    ):
        idempotency_key = idempotency_key.strip()
        
        if not idempotency_key:
            raise ValueError(
                "Idempotency key cannot be blank."
            )
            
        existing = (
            PaymentService._get_existing_idempotent_payment(
                idempotency_key=idempotency_key,
                invoice_id=invoice_id,
                provider=provider,
            )
        )
        
        if existing is None:
            return existing
        
        try:
            with transaction.atomic():
                try:
                    invoice = (
                        Invoice.objects
                        .select_for_update()
                        .get(id=invoice_id)
                    )
                
                except Invoice.DoesNotExist:
                    raise ValueError(
                        "Invoice not found."
                    )
                    
                existing = cls._get_existing_idempotent_payment(
                    idempotency_key=idempotency_key,
                    invoice_id=invoice_id,
                    provider=provider,
                )
                if existing is not None:
                    return existing
                
                if invoice.status != Invoice.Status.OPEN:
                    raise ValueError(
                            "Only open invoices can be paid."
                        )
                if invoice.total <= 0:
                    raise ValueError(
                        "An invoice must have a positive "
                            "total before payment."
                    )
                    
                payment = Payment.objects.create(
                    invoice=invoice,
                    provider=provider,
                    idempotency_key=idempotency_key,
                    amount=invoice.total,
                    currency=invoice.currency,
                    status=Payment.Status.INITIATED,
                )

        except IntegrityError:
            existing = cls._get_existing_idempotent_payment(
                idempotency_key=idempotency_key,
                invoice_id=invoice_id,
                provider=provider,
            )
            if existing is not None:
                return existing
            raise
        
        try:
            provider_client = get_payment_provider(
                provider
            )
            result = provider_client.create_payment(
                payment_id=str(payment.id),
                amount=str(payment.amount),
                currency=payment.currency,
                invoice_number=invoice.invoice_number,
            )
            
            provider_payment_id = result.get(
                "provider_payment_id", ""
            )
            checkout_url = result.get("checkout_url", "")
            provider_status = result.get("status")

            if provider_status != "PENDING":
                raise PaymentProviderError(
                    "Provider returned an unsupported initial status."
                )

            payment.provider_payment_id = provider_payment_id
            payment.checkout_url = checkout_url
            payment.status = Payment.Status.PENDING
            payment.save(
                update_fields=[
                    "provider_payment_id",
                    "checkout_url",
                    "status",
                    "updated_at",
                ]
            )
            
        except Exception as exc:
            payment.mark_failed(
                f"Unable to initialize payment: {exc}"
            )

        return cls.get_payment(payment.id)
    
class PaymentWebhookService:
    
    @staticmethod
    def process_event(
        *,
        provider: str,
        raw_body: dict,
        signature: str,
        data: dict,
        payload: dict,
    ):
        
        valid_signature = verify_payment_webhook_signature(
            provider_name="MOCK",
            raw_body=raw_body,
            signature=signature,
        )
        
        if not valid_signature:
            raise ValueError(
                "Invalid webhook signature."
            )
        
        event_id = data.get("id")
        event_type = data.get("type")
        payment_data = data.get("data")
        
        try:
            with transaction.atomic():
                event,created = (
                    WebhookEvent.objects.get_or_create(
                        provider=provider,
                        event_id=event_id,
                        defaults={
                            "event_type": event_type,
                            "payload": payload,
                            "status": WebhookEvent.Status.RECEIVED,
                        },
                    )
                )
                
                if not created:
                    if (
                        event.event_type != event_type
                        or event.payload != payload
                    ):
                        raise ValueError(
                                "This event ID was already used with "
                                "a different payload."
                            )
                        
                    if event.status == WebhookEvent.Status.PROCESSED:
                            return {
                                "event": event,
                                "duplicate": True,
                            }

                event = (
                    WebhookEvent.objects
                    .select_for_update()
                    .get(pk=event.pk)
                )
                event.status = WebhookEvent.Status.PROCESSING
                event.error_message = ""
                event.save(
                    update_fields=[
                        "status",
                        "error_message",
                        "updated_at",
                    ]
                )

                try:
                    payment = (
                        Payment.objects
                        .select_for_update()
                        .select_related("invoice")
                        .get(
                            provider=provider,
                            provider_payment_id=(
                                payment_data["provider_payment_id"]
                            ),
                        )     
                    )
                    
                except Payment.DoesNotExist:
                    event.status = WebhookEvent.Status.FAILED
                    event.error_message = (
                        "No payment matches this provider payment ID."
                    )
                    event.save(
                        update_fields=[
                            "status",
                            "error_message",
                            "updated_at"
                        ]
                    )
                    
                    return {
                        "event": event,
                        "duplicate": False,
                        "error": "payment_not_found",
                    }

                incoming_status = payment_data["status"]

                if payment.status == incoming_status:
                    pass
                
                elif (
                    payment.status == Payment.Status.SUCCEEDED
                    and incoming_status == Payment.Status.REFUNDED
                ):
                    payment.status = Payment.Status.REFUNDED
                    payment.completed_at = timezone.now()
                    payment.save(
                        update_fields=[
                            "status",
                            "completed_at",
                            "updated_at",
                        ]
                    )
                    
                elif incoming_status == Payment.Status.REFUNDED:
                    event.status = WebhookEvent.Status.FAILED
                    event.error_message = (
                        "A payment must succeed before it can be refunded."
                    )
                    event.save(
                        update_fields=[
                            "status",
                            "error_message",
                            "updated_at",
                        ]
                    )
                    return {
                        "event": event,
                        "duplicate": False,
                        "error": "invalid_transition",
                    }
                    
                elif payment.status in (
                    Payment.Status.INITIATED,
                    Payment.Status.PENDING,
                ):
                    PaymentWebhookService._apply_payment_status(
                        payment=payment,
                        incoming_status=incoming_status,
                    )
                elif (
                    payment.status == Payment.Status.SUCCEEDED
                    and incoming_status == Payment.Status.REFUNDED
                ):
                    payment.status = Payment.Status.REFUNDED
                    payment.completed_at = timezone.now()
                    payment.save(
                        update_fields=[
                            "status",
                            "completed_at",
                            "updated_at",
                        ]
                    )
                else:
                    event.status = WebhookEvent.Status.FAILED
                    event.error_message = (
                        f"Invalid payment transition: "
                        f"{payment.status} -> {incoming_status}."
                    )
                    event.save(
                        update_fields=[
                            "status",
                            "error_message",
                            "updated_at",
                        ]
                    )
                    return {
                        "event": event,
                        "duplicate": False,
                        "error": "invalid_transition",
                    }

                event.status = WebhookEvent.Status.PROCESSED
                event.processed_at = timezone.now()
                event.error_message = ""
                event.save(
                    update_fields=[
                        "status",
                        "processed_at",
                        "error_message",
                        "updated_at",
                    ]
                )

                return {
                    "event": event,
                    "duplicate": False,
                }
                
        except IntegrityError:
            existing = WebhookEvent.objects.get(
                provider=provider,
                event_id=event_id,
            )

            if existing is not None:
                if (
                    existing.event_type != event_type
                    or existing.payload != payload
                ):
                    raise ValueError(
                            "This event ID was already used with "
                            "a different payload."
                        )

                if existing.status == WebhookEvent.Status.PROCESSED:
                    return {
                        "event": existing,
                        "duplicate": True,
                    }

            raise
        
    @staticmethod
    def _apply_payment_status(
        *,
        payment,
        incoming_status,
    ):

        if incoming_status == Payment.Status.SUCCEEDED:
            payment.status = Payment.Status.SUCCEEDED
            payment.completed_at = timezone.now()
            payment.failure_reason = ""
            payment.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "failure_reason",
                    "updated_at",
                ]
            )

            invoice = (
                Invoice.objects
                .select_for_update()
                .get(pk=payment.invoice_id)
            )

            if invoice.status == Invoice.Status.OPEN:
                invoice.status = Invoice.Status.PAID
                invoice.paid_at = timezone.now()
                invoice.save(
                    update_fields=[
                        "status",
                        "paid_at",
                        "updated_at",
                    ]
                )

        elif incoming_status == Payment.Status.FAILED:
            payment.status = Payment.Status.FAILED
            payment.failure_reason = "Payment failed at provider."
            payment.completed_at = timezone.now()
            payment.save(
                update_fields=[
                    "status",
                    "failure_reason",
                    "completed_at",
                    "updated_at",
                ]
            )

        elif incoming_status == Payment.Status.CANCELED:
            payment.status = Payment.Status.CANCELED
            payment.completed_at = timezone.now()
            payment.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "updated_at",
                ]
            )

        elif incoming_status == Payment.Status.REFUNDED:
            raise ValueError(
                "A payment must succeed before \
                it can be refunded."
            )

        else:
            raise ValueError(
                "Unsupported payment status."
            )