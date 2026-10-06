import uuid 
from django.db import models

class Notification(models.Model):
    class EventType(models.TextChoices):
        USER_INVITED = "USER_INVITED", "User Invited"
        TASK_ASSIGNED = "TASK_ASSIGNED", "Task Assigned"
        TASK_COMPLETED = "TASK_COMPLETED", "Task Completed"
        PASSWORD_RESET = "PASSWORD_RESET", "Password Reset"
        SUBSCRIPTION_CREATED = (
            "SUBSCRIPTION_CREATED",
            "Subscription Created",
        )
        PAYMENT_FAILED = "PAYMENT_FAILED", "Payment Failed"
        REPORT_READY = "REPORT_READY", "Report Ready"
        
    class Status(models.TextChoices):
        UNREAD = "UNREAD", "Unread"
        READ = "READ", "Read"
        
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant_id = models.UUIDField(
        db_index=True,
    )
    user_id = models.UUIDField(
        db_index=True,
    )
    event_type = models.CharField(
        max_length=100,
        choices=EventType.choices,
    )
    title = models.CharField(
        max_length=255,
    )
    message = models.TextField()
    resource_type = models.CharField(
        max_length=100,
        blank=True,
    )
    resource_id = models.UUIDField(
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNREAD,
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    
    class Meta:
        db_table = "notifications"
        
        indexes = [
            models.Index(
                fields=["tenant_id", "user_id"],
            ),
            models.Index(
                fields=["tenant_id", "status"],
            ),
            models.Index(
                fields=["tenant_id", "event_type"],
            ),
            models.Index(
                fields=["tenant_id", "created_at"],
            ),
        ]

class NotificationPreference(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    tenant_id = models.UUIDField(
        db_index=True,
    )
    user_id = models.UUIDField(
        db_index=True,
    )
    event_type = models.CharField(
        max_length=100,
        choices=Notification.EventType.choices,
    )
    in_app_enabled = models.BooleanField(
        default=True,
    )
    email_enabled = models.BooleanField(
        default=True,
    )
    push_enabled = models.BooleanField(
        default=False,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "notification_preferences"
        
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "tenant_id",
                    "user_id",
                    "event_type",
                ],
                name="unique_notification_preference",
            ),
        ]
        
        indexes = [
            models.Index(
                fields=["tenant_id", "user_id"],
            ),
        ]
