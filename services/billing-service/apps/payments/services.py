from uuid import UUID
from django.db import transaction,IntegrityError
from django.utils import timezone
from apps.invoices.models import Invoice
from .models import Payment
from .providers import (
    PaymentProviderError,
    get_payment_provider,
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