import uuid
from django.db import models
from django.conf import settings

class AuthenticationAuditEvent(models.Model):
    class EventType(models.TextChoices):
        LOGIN_SUCCESS = "login_success", "Login Success"
        LOGIN_FAILURE = "login_failure", "Login Failure"
        LOGOUT = "logout", "Logout"
        PASSWORD_CHANGED = "password_changed", "Password Changed"
        EMAIL_VERIFIED = "email_verified", "Email Verified"
        VERIFICATION_REQUESTED = (
            "verification_requested",
            "Verification Requested",
        )
        
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authentication_audit_events",
    )
    event_type = models.CharField(
        max_length=50,
        choices=EventType.choices,
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )
    request_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "-created_at"],
                name="auth_audit_user_created_idx",
            ),
            models.Index(
                fields=["event_type", "-created_at"],
                name="auth_audit_event_created_idx",
            ),
        ]
        
    def __str__(self):
        return f"{self.event_type} - {self.created_at}"