from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from apps.common.exceptions import (
    AuthenticationError,
    ConflictError,
    ResourceNotFoundError,
)
from apps.users.models import User,EmailVerificationToken

class EmailVerificationService:
    
    @staticmethod
    @transaction.atomic
    def create_verification_token(*,email: str) -> None:
        try:
            user = User.objects.get(
                email__iexact=email,
            )
        except User.DoesNotExist:
            raise ResourceNotFoundError(
                message="User not found."
            )
        
        if user.email_verified:
            raise ConflictError(
                message="Email is already verified."
            )
            
        EmailVerificationToken.objects.filter(
            user=user,
            used_at__isnull=True,
        ).update(
            used_at=timezone.now(),
        )
        
        EmailVerificationToken.objects.create(
            user=user,
            expires_at=timezone.now() + timedelta(hours=24),
        )
        
    @staticmethod
    @transaction.atomic
    def verify_email(*,token: str) -> User:
        try:
            verification_token = (
                EmailVerificationToken.objects
                .select_related("user")
                .get(token=token)
            )
        except EmailVerificationToken.DoesNotExist:
            raise AuthenticationError(
                message="Invalid email verification token."
            )
        
        if verification_token.used_at is not None:
            raise AuthenticationError(
                message="Email verification token has already been used."
            )
            
        if verification_token.expires_at <= timezone.now():
            raise AuthenticationError(
                message="Email verification token has expired."
            )
            
        user = verification_token.user
        
        if user.email_verified:
            raise ConflictError(
                message="Email is already verified."
            )
            
        user.email_verified = True
        user.email_verified_at = timezone.now()
        
        user.save(
            update_fields=[
                "email_verified","email_verified_at","updated_at",
            ],
        )
        
        verification_token.used_at = timezone.now()
        verification_token.save(
            update_fields=["used_at"],
        )
        
        return user