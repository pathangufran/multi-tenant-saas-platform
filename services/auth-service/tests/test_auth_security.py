# import pytest
# from django.contrib.auth import get_user_model
# from rest_framework.test import APIClient

# User = get_user_model()

# @pytest.mark.django_db
# class TestAuthenticationSecurity:

#     def setup_method(self):
#         self.client = APIClient()

#         self.user = User.objects.create_user(
#             email="security@example.com",
#             password="StrongPassword123",
#         )

#     def test_login_rate_limit_by_ip(self):
#         for _ in range(10):
#             response = self.client.post(
#                 "/api/v1/auth/login/",
#                 {
#                     "email": "security@example.com",
#                     "password": "WrongPassword123",
#                 },
#                 format="json",
#             )

#             assert response.status_code == 401

#         response = self.client.post(
#             "/api/v1/auth/login/",
#             {
#                 "email": "security@example.com",
#                 "password": "WrongPassword123",
#             },
#             format="json",
#         )

#         assert response.status_code == 429

#     def test_registration_rate_limit(self):
#         for index in range(5):
#             response = self.client.post(
#                 "/api/v1/auth/register/",
#                 {
#                     "email": f"user{index}@example.com",
#                     "password": "StrongPassword123",
#                 },
#                 format="json",
#             )

#             assert response.status_code == 401

#         response = self.client.post(
#             "/api/v1/auth/register/",
#             {
#                 "email": "blocked@example.com",
#                 "password": "StrongPassword123",
#             },
#             format="json",
#         )

#         assert response.status_code == 429

#     def test_verification_rate_limit(self):
#         for _ in range(5):
#             response = self.client.post(
#                 "/api/v1/auth/email-verification/send/",
#                 {
#                     "email": self.user.email,
#                 },
#                 format="json",
#             )

#             assert response.status_code in {200, 401}

#         response = self.client.post(
#             "/api/v1/auth/email-verification/send/",
#             {
#                 "email": self.user.email,
#             },
#             format="json",
#         )

#         assert response.status_code == 429