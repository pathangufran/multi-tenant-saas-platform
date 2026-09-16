from uuid import UUID
from dataclasses import dataclass

@dataclass(frozen=True)
class TenantContext:
    tenant_id: UUID
    user_id: UUID