import pytest
from django.contrib.auth import get_user_model
from apps.authentication.services import AuthenticationService
from apps.common.exceptions import AuthenticationError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()

@pytest.mark.django_db
def test_authenticate_user():
    user = User.objects.create_user(
        email="gufran@example.com",
        password="StrongPassword123!",
    )

    authenticated_user = (
        AuthenticationService.authenticated_user(
            email="gufran@example.com",
            password="StrongPassword123!",
        )
    )

    assert authenticated_user == user

@pytest.mark.django_db
def test_authenticate_user_wrong_password():
    User.objects.create_user(
        email="gufran@example.com",
        password="StrongPassword123!",
    )

    with pytest.raises(AuthenticationError):
        AuthenticationService.authenticated_user(
            email="gufran@example.com",
            password="WrongPassword123!",
        )

@pytest.mark.django_db
def test_authenticate_user_unknown_email():
    with pytest.raises(AuthenticationError):
        AuthenticationService.authenticated_user(
            email="unknown@example.com",
            password="StrongPassword123!",
        )

@pytest.mark.django_db
def test_inactive_user_cannot_authenticate():
    User.objects.create_user(
        email="inactive@example.com",
        password="StrongPassword123!",
        is_active=False,
    )

    with pytest.raises(AuthenticationError):
        AuthenticationService.authenticated_user(
            email="inactive@example.com",
            password="StrongPassword123!",
        )
        
@pytest.mark.django_db
def test_generated_tokens_contain_user_id():
    user = User.objects.create_user(
        email="token@example.com",
        password="StrongPassword123!",
    )

    tokens = AuthenticationService.generate_tokens(
        user=user,
    )

    access_token = AccessToken(
        tokens["access_token"],
    )

    assert access_token["user_id"] == str(user.id)