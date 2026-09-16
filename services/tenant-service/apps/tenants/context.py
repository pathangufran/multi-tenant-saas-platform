from contextvars import ContextVar
from .tenant_context import TenantContext

tenant_context: ContextVar[
    TenantContext | None
] = ContextVar(
    "tenant_context",
    default=None,
)

def set_tenant_context(
    context: TenantContext,
):
    return tenant_context.set(context)

def get_tenant_context() -> TenantContext:
    context = tenant_context.get()
    
    if context is None:
        raise RuntimeError(
            "Tenant context has not been established."
        )
        
    return context

def clear_tenant_context(
    token,
) -> None:
    tenant_context.reset(token)