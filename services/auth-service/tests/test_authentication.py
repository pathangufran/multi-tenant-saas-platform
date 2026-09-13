import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()

@pytest.mark.django_db
def test_successful_login():
    User.objects.create_user(
        email="gufran@example.com",
        password="StrongPassword123!",
    )
    
    client = APIClient()
    
    response = client.post(
        "/api/v1/auth/login/",
        {
            "email": "gufran@example.com",
            "password": "StrongPassword123!",
        },
        format="json",
    )
    
    assert response.status_code == 200
    
    data = response.json()
    
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "Bearer"
    
@pytest.mark.django_db
def test_login_with_wrong_password():
    User.objects.create_user(
        email="gufran@example.com",
        password="StrongPassword123!",
    )

    client = APIClient()

    response = client.post(
        "/api/v1/auth/login/",
        {
            "email": "gufran@example.com",
            "password": "WrongPassword123!",
        },
        format="json",
    )

    assert response.status_code == 401

    data = response.json()

    assert data["error"]["code"] == "AUTHENTICATION_ERROR"
    assert data["error"]["message"] == "Invalid email or password."
    
@pytest.mark.django_db
def test_login_with_unknown_email():
    client = APIClient()

    response = client.post(
        "/api/v1/auth/login/",
        {
            "email": "unknown@example.com",
            "password": "StrongPassword123!",
        },
        format="json",
    )

    assert response.status_code == 401

    data = response.json()

    assert data["error"]["code"] == "AUTHENTICATION_ERROR"
    assert data["error"]["message"] == "Invalid email or password."
    
@pytest.mark.django_db
def test_inactive_user_cannot_login():
    User.objects.create_user(
        email="inactive@example.com",
        password="StrongPassword123!",
        is_active=False,
    )

    client = APIClient()

    response = client.post(
        "/api/v1/auth/login/",
        {
            "email": "inactive@example.com",
            "password": "StrongPassword123!",
        },
        format="json",
    )

    assert response.status_code == 401

    data = response.json()

    assert data["error"]["code"] == "AUTHENTICATION_ERROR"
    
def test_invalid_email():
    client = APIClient()

    response = client.post(
        "/api/v1/auth/login/",
        {
            "email": "not-an-email",
            "password": "StrongPassword123!",
        },
        format="json",
    )

    assert response.status_code == 400
    
def test_missing_password():
    client = APIClient()

    response = client.post(
        "/api/v1/auth/login/",
        {
            "email": "gufran@example.com",
        },
        format="json",
    )

    assert response.status_code == 400