import pytest
from apps.users.models import User
from apps.users.services import UserService
from apps.common.exceptions import ConflictError

@pytest.mark.django_db
def test_register_user_service():
    user = UserService.register_user(
        email="gufran@example.com",
        password="StrongPassword123!",
        first_name="Gufran",
        last_name="Pathan",
    )

    assert user.email == "gufran@example.com"
    assert user.first_name == "Gufran"
    assert user.last_name == "Pathan"
    assert user.check_password("StrongPassword123!")

@pytest.mark.django_db
def test_register_user_rejects_duplicate_email():
    UserService.register_user(
        email="gufran@example.com",
        password="StrongPassword123!",
    )

    with pytest.raises(ConflictError):
        UserService.register_user(
            email="GUFRAN@example.com",
            password="AnotherPassword123!",
        )