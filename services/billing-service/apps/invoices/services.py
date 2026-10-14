import uuid
from uuid import UUID 
from decimal import Decimal
from datetime import timedelta
from django.db import transaction,IntegrityError
from django.utils import timezone
from .models import Invoice,InvoiceLineItem
from apps.subscriptions.models import Subscription

class InvoiceService:
    
    @staticmethod
    def list_invoices(
        *,
        tenant_id=None,
        status=None,
    ) -> Invoice:
        invoices = (
            Invoice.objects
            .select_related("subscription")
            .prefetch_related("line_items")
        )
        
        if tenant_id is not None:
            invoices = invoices.filter(
                tenant_id=tenant_id,
            )
        if status is not None:
            invoices = invoices.filter(
                status=status,
            )
            
        return invoices.order_by("-issued_at")
    
    @staticmethod
    def get_invoice(
        *,
        invoice_id: UUID, 
    ) -> Invoice:
        try:
            return (
                Invoice.objects
                .select_related("subscription")
                .prefetch_related("line_items")
                .get(id=invoice_id)
            )
            
        except Invoice.DoesNotExist:
            raise ValueError(
                "Invoice not found."
            )
            
    @staticmethod
    def get_invoice_by_number(
        *,
        invoice_number: str,
    ) -> Invoice:
        try:
            return (
                Invoice.objects
                .select_related("subscription")
                .prefetch_related("line_items")
                .get(invoice_number=invoice_number)
            )
        
        except Invoice.DoesNotExist:
            raise ValueError(
                "Invoice not found."
            )
        
    @staticmethod
    @transaction.atomic
    def generate_invoice(
        *,
        subscription_id: UUID,
        tax_amount=Decimal("0.00"),
        due_days=7,
    ) -> Invoice:
        
        try:
            subscription = (
                Subscription.objects
                .select_for_update()
                .select_related("plan")
                .get(id=subscription_id)
            )
        
        except Subscription.DoesNotExist:
            raise ValueError(
                "Subscription not found."
            )
            
        if subscription.status not in (
            Subscription.Status.ACTIVE,
            Subscription.Status.PAST_DUE,
        ):
            raise ValueError(
                "Invoices can only be generated for \
                active or past-due subscriptions."
            )
        
        if tax_amount < Decimal("0.00"):
            raise ValueError(
                "Tax amount cannot be negative."
            )
        if due_days < 0 or due_days > 365:
            raise ValueError(
                "Due days must be between 0 and 365."
            )
            
        existing_invoice = (
            Invoice.objects.get(
                subscription=subscription,
                period_start=(
                    Subscription.
                    current_period_start,
                ),
                period_end=(
                    Subscription.
                    current_period_end,
                ),
            )
        )
        
        if existing_invoice is not None:
            raise ValueError(
                "An invoice already exists for \
                this subscription period."
            )
            
        plan = subscription.plan
        subtotal = (
            plan.price.quantize(Decimal("0.01"))
        )
        tax_amount = (
            Decimal(tax_amount).
            quantize(Decimal("0.01")),
        )
        total = (
            (subtotal + tax_amount).
            quantize(Decimal("0.01")),
        )
        issued_at = timezone.now()
        due_at = issued_at + timedelta(days=due_days)
        invoice_number = (
            f"INV-{issued_at:%Y%m}-{uuid.uuid4().hex[:12].upper()}"
        )

        try:
            with transaction.atomic():
                invoice = Invoice.objects.create(
                    invoice_number=invoice_number,
                    tenant_id=subscription.tenant_id,
                    subscription=subscription,
                    plan_code=plan.code,
                    plan_name=plan.name,
                    currency=plan.currency,
                    billing_interval=plan.billing_interval,
                    period_start=subscription.current_period_start,
                    period_end=subscription.current_period_end,
                    subtotal=subtotal,
                    tax_amount=tax_amount,
                    total=total,
                    status=Invoice.Status.OPEN,
                    issued_at=issued_at,
                    due_at=due_at,
                )
                
                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    description=(
                        f"{plan.name} subscription "
                        f"({plan.billing_interval.lower()})"
                    ),
                    quantity=1,
                    unit_price=subtotal,
                    amount=subtotal,
                )
                
        except IntegrityError:
            raise ValueError(
                "An invoice for this subscription \
                period already exists."
            )
            
        return (
            Invoice.objects
            .select_related("subscription")
            .prefetch_related("line_items")
            .get(id=invoice.id)
        )
        
    @staticmethod
    @transaction.atomic
    def void_invoice(
        *,
        invoice_id: UUID,
    ) -> Invoice:
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
            
        if invoice.status == Invoice.Status.PAID:
            raise ValueError(
                "A paid invoice cannot be voided."
            )
        if invoice.status == Invoice.Status.UNCOLLECTIBLE:
            raise ValueError(
                "An uncollectible invoice cannot be voided."
            )
        if invoice.status == Invoice.Status.VOID:
            return invoice
        
        invoice.status = Invoice.Status.VOID
        invoice.voided_at = timezone.now()
        invoice.save(
            update_fields=[
                "status","voided_at","updated_at",
            ]
        )
        
        return invoice
        
        
        
        