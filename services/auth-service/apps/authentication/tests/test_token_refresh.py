import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from apps.authentication.services import (
    AuthenticationService,
)

User = get_user_model()

@pytest.mark.django_db
def test_refresh_token():
    user = User.objects.create_user(
        email="gufran@example.com",
        password="StrongPassword123!",
    )

    tokens = AuthenticationService.login(
        email="gufran@example.com",
        password="StrongPassword123!",
    )

    client = APIClient()

    response = client.post(
        "/api/v1/auth/token/refresh/",
        {
            "refresh_token": tokens["refresh_token"],
        },
        format="json",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "Bearer"
    
def test_invalid_refresh_token():
    client = APIClient()

    response = client.post(
        "/api/v1/auth/token/refresh/",
        {
            "refresh_token": "invalid-token",
        },
        format="json",
    )

    assert response.status_code == 401

    data = response.json()

    assert data["error"]["code"] == (
        "AUTHENTICATION_ERROR"
    )
    
def test_missing_refresh_token():
    client = APIClient()

    response = client.post(
        "/api/v1/auth/token/refresh/",
        {},
        format="json",
    )

    assert response.status_code == 400
    
@pytest.mark.django_db
def test_refresh_token_rotation():
    User.objects.create_user(
        email="rotation@example.com",
        password="StrongPassword123!",
    )

    tokens = AuthenticationService.login(
        email="rotation@example.com",
        password="StrongPassword123!",
    )

    old_refresh_token = tokens["refresh_token"]

    client = APIClient()

    response = client.post(
        "/api/v1/auth/token/refresh/",
        {
            "refresh_token": old_refresh_token,
        },
        format="json",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["refresh_token"]
    assert data["refresh_token"] != old_refresh_token
    
@pytest.mark.django_db
def test_old_refresh_token_is_rejected_after_rotation():
    User.objects.create_user(
        email="replay@example.com",
        password="StrongPassword123!",
    )

    tokens = AuthenticationService.login(
        email="replay@example.com",
        password="StrongPassword123!",
    )

    old_refresh_token = tokens["refresh_token"]

    client = APIClient()

    first_response = client.post(
        "/api/v1/auth/token/refresh/",
        {
            "refresh_token": old_refresh_token,
        },
        format="json",
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/api/v1/auth/token/refresh/",
        {
            "refresh_token": old_refresh_token,
        },
        format="json",
    )

    assert second_response.status_code == 401