from apps.authentication.models import (
    AuthenticationAuditEvent,
)

class AuthenticationAuditService:
    
    @staticmethod
    def record(
        *,
        event_type: str,
        user=None,
        ip_address: str | None = None,
        request_id: str | None = None,
        metadata: dict | None = None,
    ) -> AuthenticationAuditEvent:
        
        return AuthenticationAuditEvent.objects.create(
            event_type=event_type,
            user=user,
            ip_address=ip_address,
            request_id=request_id,
            metadata=metadata or {},
        )