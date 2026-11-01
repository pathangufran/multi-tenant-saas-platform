import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

@pytest.mark.django_db
class TestCurrentUser:
    
    def setup_method(self):
        self.client = APIClient()
        
        self.user = User.objects.create_user(
            email="current@example.com",
            password="StrongPassword123",
            first_name="Gufran",
            last_name="Pathan",
        )
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
    def test_authenticated_user_can_get_current_user(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.access_token}",
        )

        response = self.client.get("/api/v1/auth/me/",)

        assert response.status_code == 200

        assert response.data["id"] == str(self.user.id)
        assert response.data["email"] == "current@example.com"
        assert response.data["first_name"] == "Gufran"
        assert response.data["last_name"] == "Pathan"
        assert response.data["is_active"] is True
        
    def test_unauthenticated_user_cannot_get_current_user(self):
        response = self.client.get("/api/v1/auth/me/",)

        assert response.status_code == 401

    def test_invalid_access_token_cannot_get_current_user(self):
        self.client.credentials(
            HTTP_AUTHORIZATION="Bearer invalid-access-token",
        )

        response = self.client.get("/api/v1/auth/me/",)

        assert response.status_code == 401