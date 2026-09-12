import uuid
import pytest
from apps.users.models import User
from django.db import IntegrityError
from django.contrib.auth import get_user_model

def test_django_uses_custom_user_model():
    assert get_user_model() is User

@pytest.mark.django_db
def test_email_is_username_field():
    assert User.USERNAME_FIELD == "email"

def test_no_required_fields_for_user_creation():
    assert User.REQUIRED_FIELDS == []

@pytest.mark.django_db
def test_user_can_be_created():
    user = User.objects.create_user(
        email="gufran@example.com",
        password="StrongPassword123!",
        first_name="Gufran",
        last_name="Pathan",
    )

    assert user.email == "gufran@example.com"
    assert user.first_name == "Gufran"
    assert user.last_name == "Pathan"

@pytest.mark.django_db
def test_user_has_uuid_primary_key():
    user = User.objects.create_user(
        email="uuid@example.com",
        password="StrongPassword123!",
    )

    assert isinstance(user.id, uuid.UUID)

@pytest.mark.django_db
def test_email_is_normalized():
    user = User.objects.create_user(
        email="  GUFRAN@EXAMPLE.COM  ",
        password="StrongPassword123!",
    )

    assert user.email == "gufran@example.com"

@pytest.mark.django_db
def test_password_is_hashed():
    password = "StrongPassword123!"

    user = User.objects.create_user(
        email="password@example.com",
        password=password,
    )

    assert user.password != password
    assert user.check_password(password)

@pytest.mark.django_db
def test_wrong_password_fails():
    user = User.objects.create_user(
        email="wrong@example.com",
        password="StrongPassword123!",
    )

    assert not user.check_password("WrongPassword123!")

@pytest.mark.django_db
def test_user_is_active_by_default():
    user = User.objects.create_user(
        email="active@example.com",
        password="StrongPassword123!",
    )

    assert user.is_active is True

@pytest.mark.django_db
def test_user_is_not_staff_by_default():
    user = User.objects.create_user(
        email="staff@example.com",
        password="StrongPassword123!",
    )

    assert user.is_staff is False

@pytest.mark.django_db
def test_email_is_case_insensitive_unique():
    User.objects.create_user(
        email="gufran@example.com",
        password="StrongPassword123!",
    )

    with pytest.raises(IntegrityError):
        User.objects.create_user(
            email="GUFRAN@example.com",
            password="AnotherPassword123!",
        )

@pytest.mark.django_db
def test_create_superuser():
    user = User.objects.create_superuser(
        email="admin@example.com",
        password="StrongPassword123!",
    )

    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.is_active is True
