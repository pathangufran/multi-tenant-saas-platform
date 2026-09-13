import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

@pytest.mark.django_db
def test_successful_registration():
    client = APIClient()

    response = client.post(
        "/api/v1/auth/register/",
        {
            "email": "gufran@example.com",
            "password": "StrongPassword123!",
            "first_name": "Gufran",
            "last_name": "Pathan",
        },
        format="json",
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "gufran@example.com"
    assert data["first_name"] == "Gufran"
    assert data["last_name"] == "Pathan"
    assert data["id"]
    assert "password" not in data

    user = User.objects.get(
        email="gufran@example.com"
    )
    assert user.check_password(
        "StrongPassword123!"
    )

@pytest.mark.django_db
def test_email_is_normalized():
    client = APIClient()

    response = client.post(
        "/api/v1/auth/register/",
        {
            "email": "  GUFRAN@EXAMPLE.COM  ",
            "password": "StrongPassword123!",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.json()["email"] == "gufran@example.com"

@pytest.mark.django_db
def test_duplicate_email_is_rejected():
    client = APIClient()

    payload =  {
        "email": "gufran@example.com",
        "password": "StrongPassword123!",
    }
    first_response = client.post(
        "/api/v1/auth/register/",
        payload,
        format="json", 
    )
    second_response = client.post(
        "/api/v1/auth/register/",
        payload,
        format="json",
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409

@pytest.mark.django_db
def test_duplicate_email_is_case_insensitive():
    client = APIClient()

    client.post(
        "/api/v1/auth/register/",
        {
            "email": "gufran@example.com",
            "password": "StrongPassword123!",
        },
        format="json",
    )

    response = client.post(
        "/api/v1/auth/register/",
        {
            "email": "GUFRAN@EXAMPLE.COM",
            "password": "AnotherPassword123!",
        },
        format="json",
    )

    assert response.status_code == 409


def test_invalid_email_is_rejected():
    client = APIClient()

    response = client.post(
        "/api/v1/auth/register/",
        {
            "email": "not-an-email",
            "password": "StrongPassword123!",
        },
        format="json",
    )

    assert response.status_code == 400


def test_short_password_is_rejected():
    client = APIClient()

    response = client.post(
        "/api/v1/auth/register/",
        {
            "email": "gufran@example.com",
            "password": "123",
        },
        format="json",
    )

    assert response.status_code == 400


def test_password_with_leading_whitespace_is_rejected():
    client = APIClient()

    response = client.post(
        "/api/v1/auth/register/",
        {
            "email": "gufran@example.com",
            "password": " StrongPassword123!",
        },
        format="json",
    )

    assert response.status_code == 400