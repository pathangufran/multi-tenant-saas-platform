import uuid
from django.db import models
from .managers import UserManager
from django.db.models.functions import Lower
from django.contrib.auth.models import (
    AbstractBaseUser,PermissionsMixin
)

class User(AbstractBaseUser,PermissionsMixin):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    email = models.EmailField(
        unique=True,
        db_index=True,
    )
    first_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    last_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )
    is_staff = models.BooleanField(
        default=False,
    )
    email_verified = models.BooleanField(
        default=False,
    )
    email_verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    date_joined = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    objects = UserManager()

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["-date_joined"]
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="users_user_email_ci_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["date_joined"]),
        ]

    def __str__(self):
        return self.email
    
class EmailVerificationToken(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
    )
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user","-created_at"],
                name="email_verify_user_created_idx",
            ),
        ]
        
    def __str__(self):
        return f"Email verification token for {self.user.email}"