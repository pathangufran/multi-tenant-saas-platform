from django.db import transaction
from django.utils import timezone
from .models import (
    Notification,
    NotificationPreference,
)

class NotificationService:
    
    @staticmethod
    def _get_preference(
        *,
        tenant_id,
        user_id,
        event_type,
    ):
        
        preference, _ = (
            NotificationPreference.objects.get_or_create(
                tenant_id=tenant_id,
                user_id=user_id,
                event_type=event_type,
            )
        )
        
        return preference
    
    @staticmethod
    def is_in_app_enabled(
        *,
        tenant_id,
        user_id,
        event_type,
    ):
        
        preference = NotificationService._get_preference(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
        )
        
        return preference.in_app_enabled
    
    @staticmethod
    @transaction.atomic
    def create_notification(
        *,
        tenant_id,
        user_id,
        event_type,
        title,
        message,
        resource_type="",
        resource_id=None,
        metadata=None,
    ):
        
        if not tenant_id:
            raise ValueError(
                "tenant_id is required."
            )
            
        if not user_id:
            raise ValueError(
                "user_id is required."
            )
            
        if not event_type:
            raise ValueError(
                "event_type is required."
            )
            
        if not title.strip():
            raise ValueError(
                "Notification title is required."
            )

        if not message.strip():
            raise ValueError(
                "Notification message is required."
            )
            
        if not NotificationService.is_in_app_enabled(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
        ):
            return None
        
        return Notification.objects.create(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            title=title.strip(),
            message=message.strip(),
            resource_type=resource_type.strip(),
            resource_id=resource_id,
            metadata=metadata or {},
        )
        
    @staticmethod
    def mark_as_read(
        *,
        tenant_id,
        user_id,
        notification_id,
    ):
        
        notification = Notification.objects.filter(
            id=notification_id,
            tenant_id=tenant_id,
            user_id=user_id,
        ).first()
        
        if notification is None:
            return None
        
        notification.status = Notification.Status.READ
        notification.read_at = timezone.now()
        
        notification.save(
            update_fields=[
                "status","read_at",
            ],
        )

        return notification
        
    @staticmethod
    def mark_as_unread(
        *,
        tenant_id,
        user_id,
        notification_id,
    ):
        
        notification = Notification.objects.filter(
            id=notification_id,
            tenant_id=tenant_id,
            user_id=user_id,
        ).first()
        
        if notification is None:
            return None
        
        notification.status = Notification.Status.UNREAD
        notification.read_at = None
        
        notification.save(
            update_fields=[
                "status","read_at",
            ],
        )

        return notification
    
    @staticmethod
    def list_notifications(
        *,
        tenant_id,
        user_id,
    ):
        
        return Notification.objects.filter(
            tenant_id=tenant_id,
            user_id=user_id,
        ).order_by("-created_at")
        
    @staticmethod
    def unread_count(
        *,
        tenant_id,
        user_id,
    ):
        
        return Notification.objects.filter(
            tenant_id=tenant_id,
            user_id=user_id,
            status=Notification.Status.UNREAD
        ).count()
    