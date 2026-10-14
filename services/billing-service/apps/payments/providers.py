import uuid
from uuid import UUID

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