import logging
from celery import Task
from apps.failed_jobs.services import FailedJobService

logger = logging.getLogger(__name__)

class BaseTask(Task):
    
    abstract = True
    
    def build_context(self):
        
        request = self.request
        
        return TaskExecutionContext(
            task_id=request.id,
            task_name=self.name,
            request_id=getattr(
                request,
                "request_id",
                None,
            ),
            tenant_id=getattr(
                request,
                "tenant_id",
                None,
            ),
            user_id=getattr(
                request,
                "user_id",
                None,
            ),
        )
        
    def log_start(
        self,
        context,
        **extra,
    ):
        logger.info(
            "celery_task_started",
            extra={
                "task_id": context.task_id,
                "task_name": context.task_name,
                "request_id": context.request_id,
                "tenant_id": context.tenant_id,
                "user_id": context.user_id,
                **extra,
            },
        )
        
    def log_success(
        self,
        context,
        **extra,
    ):
        logger.info(
            "celery_task_completed",
            extra={
                "task_id": context.task_id,
                "task_name": context.task_name,
                "request_id": context.request_id,
                "tenant_id": context.tenant_id,
                "user_id": context.user_id,
                **extra,
            },
        )
        
    def log_failure(
        self,
        context,
        exc,
        **extra,
    ):
        logger.exception(
            "celery_task_failed",
            extra={
                "task_id": context.task_id,
                "task_name": context.task_name,
                "request_id": context.request_id,
                "tenant_id": context.tenant_id,
                "user_id": context.user_id,
                "error": str(exc),
                **extra,
            },
        )
        
    def on_failure(
        self,
        exc,
        task_id,
        args,
        kwargs,
        einfo,
    ):
        """
        Store a failed job only when the task has exhausted
        its configured retry attempts.

        Intermediate retry failures must NOT create
        dead-letter records.
        """
        
        request = self.request
        retry_count = getattr(
            request,
            "retries",
            0,
        )
        max_retries = getattr(
            self,
            "max_retries",
            None,
        )
        retries_exhausted = (
            max_retries is not None
            and retry_count >= max_retries
        )
        if retries_exhausted:
            context = self.build_context()
            
            try:
                FailedJobService.record_failure(
                    task_id=task_id,
                    task_name=self.name,
                    exception=exc,
                    retry_count=retry_count,
                    tenant_id=context.tenant_id,
                    user_id=context.user_id,
                    request_id=context.request_id,
                    traceback=str(einfo),
                    task_args=list(args or []),
                    task_kwargs=dict(
                        kwargs or {},
                    ),
                    metadata={
                        "max_retries": max_retries,
                    },
                )    
                
            except Exception:
                logger.exception(
                    "failed_to_record_dead_letter",
                    extra={
                        "task_id": task_id,
                        "task_name": self.name,
                    },
                )
                
        return super().on_failure(
            exc,
            task_id,
            args,
            kwargs,
            einfo,
        )

        
        