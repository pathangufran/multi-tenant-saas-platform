import uuid
from uuid import UUID
import hashlib
import hmac
from django.conf import settings    

class PaymentProviderError(Exception):
    """Raised when a payment provider cannot 
    create an attempt."""

class MockPaymentProvider:
    provider_name = "MOCK"

    def create_payment(
        self,
        *,
        payment_id: UUID,
        amount: int,
        currency: str,
        invoice_number: str,
    ):
        provider_payment_id = f"mock_{uuid.uuid4().hex}"

        return {
            "provider_payment_id": provider_payment_id,
            "checkout_url": (
                "https://payments.example.invalid/checkout/"
                f"{provider_payment_id}"
            ),
            "status": "PENDING",
        }

def get_payment_provider(provider_name):
    if provider_name == "MOCK":
        return MockPaymentProvider()

    raise PaymentProviderError(
        f"Unsupported payment provider: {provider_name}"
    )

def verify_payment_webhook_signature(
    *,
    provider_name,
    raw_body,
    signature,
):
    if provider_name != "MOCK":
        return False

    secret = getattr(settings, "PAYMENT_WEBHOOK_SECRET", "")

    if not secret or not signature:
        return False

    expected_signature = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    supplied_signature = signature.strip()

    if supplied_signature.startswith("sha256="):
        supplied_signature = supplied_signature[len("sha256="):]

    return hmac.compare_digest(
        expected_signature,
        supplied_signature,
    )

def generate_mock_webhook_signature(raw_body, secret):
    """Utility for local development and tests only."""
    return hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()