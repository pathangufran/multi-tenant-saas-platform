from celery import shared_task
from .task_infrastructure import BaseTask

@shared_task(
    bind=True,
    base=BaseTask,
    name="apps.common.tasks.health_check_task"
)
def health_check_task(self):
    """
    Basic task used to verify Celery execution.
    """
    
    context = self.build_context()
    
    self.log_start(context)
    
    try:
        result = "Celery is working."
        
        self.log_success(context)
        
        return result
    
    except Exception as exc:
        self.log_failure(context,exc)
        raise 
    
@shared_task(
    bind=True,
    base=BaseTask,
    name="apps.common.tasks.idempotent_task"
)
def idempotent_task(self,operation_id: str):
    """
    Demonstrates the idempotency foundation.

    Only the first execution for a given operation_id
    performs the operation.
    """
    
    context = self.build_context()
    
    self.log_start(
        context,
        operation_id=operation_id,
    )
    
    idempotency_key, acquired = self.acquire_idempotency(
        operation="common-task",
        identifier=operation_id,
    )
    
    if not acquired:
        self.log_success(
            context,
            operation_id=operation_id,
            skipped=True,
        )
        
        return {
            "status": "already_processed",
            "operation_id": operation_id,
        }
    
    try:
        result = {
            "status": "processed",
            "operation_id": operation_id,
        }
        
        self.log_success(
            context,
            operation_id=operation_id,
        )
        
        return result

    except Exception as exc:
        self.release_idempotency(idempotency_key)
        
        self.log_failure(
            context,
            exc,
            operation_id=operation_id,
        )
        raise
        