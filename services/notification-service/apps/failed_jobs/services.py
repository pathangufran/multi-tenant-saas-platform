from uuid import UUID
from datetime import datetime,timezone
from typing import Any
from django.db import transaction
from .models import FailedJobs

class FailedJobService:
    
    @staticmethod
    @transaction.atomic
    def record_failure(
        *,
        task_id: str,
        task_name: str,
        exception: Exception,
        retry_count: int = 0,
        tenant_id=None,
        user_id=None,
        request_id: str | None = None,
        traceback: str = "",
        task_args: list | None = None,
        task_kwargs: dict | None = None,
        metadata: dict | None = None,
    ) -> FailedJobs:
        
        return FailedJobs.objects.create(
            task_id=task_id,
            task_name=task_name,
            tenant_id=tenant_id,
            user_id=user_id,
            request_id=request_id,
            status=FailedJobs.Status.FAILED,
            retry_count=retry_count,
            exception_type=(
                f"{exception.__class__.__module__}."
                f"{exception.__class__.__name__}"
            ),
            error_message=str(exception),
            traceback=traceback or "",
            task_args=task_args or [],
            task_kwargs=task_kwargs or {},
            metadata=metadata or {},
        )
        
    @staticmethod
    def list_failures(
        *,
        tenant_id=None,
        task_name: str | None = None,
        status: str | None = None,
    ) -> FailedJobs:
        
        queryset = FailedJobs.objects.all()
        
        if tenant_id is not None:
            queryset = queryset.filter(
                tenant_id=tenant_id,
            )
        if task_name is not None:
            queryset = queryset.filter(
                task_name=task_name,
            )
        if status is not None:
            queryset = queryset.filter(
                status=status,
            )
            
        return queryset.order_by("-created_at")
    
    @staticmethod
    def get_failure(
        *,
        failure_id: UUID,
    ) -> FailedJobs:
        
        return FailedJobs.objects.get(
            id=failure_id,
        )
        
    @staticmethod
    @transaction.atomic
    def resolve_failure(
        *,
        failure_id: UUID,
        resolution_notes: str = "",   
    ) -> FailedJobs:
        
        failure = FailedJobService.get_failure(
            failure_id=failure_id,
        )
        
        failure.status = FailedJobs.Status.RESOLVED
        failure.resolved_at = datetime.now(
            timezone.utc,
        )
        failure.resolution_notes = resolution_notes
        
        failure.save(
            update_fields=[
                "status",
                "resolved_at",
                "resolution_notes",
            ],
        )
        
        return failure
        