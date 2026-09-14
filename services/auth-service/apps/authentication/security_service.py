from apps.common.exceptions import RateLimitError
from apps.common.rate_limit import (
    RateLimitExceeded,
    RateLimiter,
)

class AuthenticationSecurityService:

    LOGIN_IP_LIMIT = 10
    LOGIN_EMAIL_LIMIT = 5
    REGISTRATION_IP_LIMIT = 5
    VERIFICATION_IP_LIMIT = 5
    PASSWORD_CHANGE_USER_LIMIT = 5
    WINDOW_SECONDS = 60

    @classmethod
    def check_login_limits(
        cls,
        *,
        ip_address: str,
        email: str,
    ) -> None:
        try:
            RateLimiter.check(
                key=f"login:ip:{ip_address}",
                limit=cls.LOGIN_IP_LIMIT,
                window=cls.WINDOW_SECONDS,
            )
            RateLimiter.check(
                key=f"login:email:{email.lower()}",
                limit=cls.LOGIN_EMAIL_LIMIT,
                window=cls.WINDOW_SECONDS,
            )

        except RateLimitExceeded:
            raise RateLimitError()

    @classmethod
    def check_registration_limit(
        cls,
        *,
        ip_address: str,
    ) -> None:
        try:
            RateLimiter.check(
                key=f"registration:ip:{ip_address}",
                limit=cls.REGISTRATION_IP_LIMIT,
                window=cls.WINDOW_SECONDS,
            )

        except RateLimitExceeded:
            raise RateLimitError()

    @classmethod
    def check_verification_limit(
        cls,
        *,
        ip_address: str,
    ) -> None:
        try:
            RateLimiter.check(
                key=f"verification:ip:{ip_address}",
                limit=cls.VERIFICATION_IP_LIMIT,
                window=cls.WINDOW_SECONDS,
            )

        except RateLimitExceeded:
            raise RateLimitError()

    @classmethod
    def check_password_change_limit(
        cls,
        *,
        user_id: str,
    ) -> None:
        try:
            RateLimiter.check(
                key=f"password-change:user:{user_id}",
                limit=cls.PASSWORD_CHANGE_USER_LIMIT,
                window=cls.WINDOW_SECONDS,
            )

        except RateLimitExceeded:
            raise RateLimitError()