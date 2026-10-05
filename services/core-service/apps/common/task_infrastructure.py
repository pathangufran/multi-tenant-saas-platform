import logging
import uuid
from dataclasses import dataclass
from typing import Any
from celery import Task
from django.core.cache import cache

logger = logging.getLogger(__name__)

class TaskInfrastructureError(Exception):
    """Base exception for task infrastructure errors."""
    
class PermanentTaskError(TaskInfrastructureError):
    """
    Error that should not normally be retried.
    """
    
class TransientTaskError(TaskInfrastructureError):
    """
    Error that may be retried by the task retry policy.
    """
    
@dataclass(frozen=True)
class TaskExecutionContext:
    task_id: str
    task_name: str
    request_id: str | None = None
    tenant_id: str | None = None
    user_id: str | None = None
    
class TaskIdempotency:
    """
    Small Redis-backed idempotency foundation.

    The key is created atomically with a TTL.
    If the key already exists, the operation is considered
    already in progress or already processed.
    """
    
    PREFIX = "celery:idempotency"
    
    @classmethod
    def _key(cls,key: str) -> str:
        return f"{cls.PREFIX}:{key}"
    
    @classmethod
    def acquire(
        cls,
        key: str,
        *,
        ttl: int = 3600,
    ) -> bool:
        
        if not key:
            raise ValueError(
                "Idempotency key cannot be empty."
            )
            
        return bool(
            cache.add(
                cls._key(key),
                "1",
                timeout=ttl,
            )
        )
        
    @classmethod
    def release(cls,key: str) -> None:
        
        if not key:
            return
        
        cache.delete(cls._key(key))
        
class BaseTask(Task):
    """
    Shared Celery task base.

    Provides:
    - task execution context
    - structured lifecycle logging
    - safe exception logging
    - idempotency foundation
    """
    
    abstract = True
    
    idempotency_ttl = 3600
    
    def build_context(
        self,
        *,
        request_id: str | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None, 
    ) ->  TaskExecutionContext:
        
        return TaskExecutionContext(
            task_id=str(self.request.id),
            task_name=self.name,
            request_id=request_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        
    def log_start(
        self,
        context: TaskExecutionContext,
        **extra: Any,
    ) -> None:
        
        logger.info(
            "celery_task_started",
            extra={
                "task_id": context.task_id,
                "task_name": context.task_name,
                "request_id": context.request_id,
                "tenant_id": context.tenant_id,
                "user_id": context.user_id,
                **extra
            },
        )
        
    def log_success(
        self,
        context: TaskExecutionContext,
        **extra: Any,
    ) -> None:
        
        logger.info(
            "celery_task_completed",
            extra={
                "task_id": context.task_id,
                "task_name": context.task_name,
                "request_id": context.request_id,
                "tenant_id": context.tenant_id,
                "user_id": context.user_id,
                **extra
            },
        )
        
    def log_failure(
        self,
        context: TaskExecutionContext,
        exc: Exception,
        **extra: Any,
    ) -> None:
        
        logger.info(
            "celery_task_failed",
            extra={
                "task_id": context.task_id,
                "task_name": context.task_name,
                "request_id": context.request_id,
                "tenant_id": context.tenant_id,
                "user_id": context.user_id,
                "exception_type": type(exc).__name__,
                **extra
            },
        )
        
    def generate_idempotency_key(
        self,
        *,
        operation: str,
        identifier: str,
    ) -> str:
        
        if not operation.strip():
            raise ValueError(
                "Operation cannot be empty."
            )
        if not identifier.strip():
            raise ValueError(
                "Identifier cannot be empty."
            )
            
        return f"{operation}:{identifier}"
    
    def acquire_idempotency(
        self,
        *,
        operation: str,
        identifier: str,
    ) -> tuple[str, bool]:
        
        key = self.generate_idempotency_key(
            operation=operation,
            identifier=identifier,
        )
        
        acquired = TaskIdempotency.acquire(
            key,
            ttl=self.idempotency_ttl,
        )
        
        return key, acquired
    
    def release_idempotency(self,key: str) -> None:
        
        TaskIdempotency.release(key)