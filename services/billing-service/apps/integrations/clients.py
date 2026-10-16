import requests
from django.conf import settings

class IntegrationError(Exception):
    """Base exception for internal 
    service integration errors."""

class RemoteServiceUnavailable(IntegrationError):
    pass

class RemoteServiceRejected(IntegrationError):
    pass

class TenantServiceClient:
    
    @staticmethod
    def validate_tenant(tenant_id):
        base_url = (
            settings.TENANT_SERVICE_URL.rstrip("/")
        )
        url = f"{base_url}/api/internal/v1/tenants/validate"
        
        headers = {
            "X-Internal-Service-Key": (
                settings.INTERNAL_SERVICE_KEY,
            ),
            "Content-Type": "application/json",
        }
        
        try:
            response = requests.post(
                url,
                json={"tenant_id": str(tenant_id),},
                headers=headers,
                timeout=settings.INTEGRATION_TIMEOUT_SECONDS,
            )
        
        except requests.RequestException as exc:
            raise RemoteServiceUnavailable(
                "Tenant Service could not be reached."
            ) from exc
            
        if response.status_code in (401,403):
            raise RemoteServiceRejected(
                "Tenant Service rejected internal authentication."
            )
        if response.status_code == 404:
            raise RemoteServiceRejected(
                "Tenant does not exists."
            )
        if response.status_code >= 500:
            raise RemoteServiceUnavailable(
                "Tenant Service returned a server error."
            )
        if not response.ok:
            raise RemoteServiceRejected(
                "Tenant Service rejected the validation request."
            )
            
        try:
            data = response.json()
            
        except ValueError as exc:
            raise RemoteServiceUnavailable(
                "Tenant Service returned invalid JSON."
            ) from exc
            
        if str(data.get("id")) != str(tenant_id):
            raise RemoteServiceUnavailable(
                "Tenant Service returned an unexpected tenant."
            )
        if data.get("status") != "ACTIVE":
            raise RemoteServiceRejected(
                "The tenant is not active."
            )
            
        return data