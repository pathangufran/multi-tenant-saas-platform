from django.contrib.auth import get_user_model
from django.db import IntegrityError,transaction
from apps.common.exceptions import ConflictError
from datetime import timedelta
from django.utils import timezone
from .models import EmailVerificationToken

User = get_user_model()

class UserService:

    @staticmethod
    @transaction.atomic
    def register_user(
        *,
        email: str,
        password: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ):
        email = email.lower().strip()

        if User.objects.filter(
            email__iexact=email
        ).exists():
            raise ConflictError(
                message="A user with this email " \
                "already exists."
            )

        try:
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
            
            EmailVerificationToken.objects.create(
                user=user,
                expires_at=timezone.now() + timedelta(hours=24)
            )

        except IntegrityError:
            raise ConflictError(
                message="A user with this email " \
                "already exists."
            )

        return user
        