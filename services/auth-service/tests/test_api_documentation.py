import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
class TestAPIDocumentation:
    
    def setup_method(self):
        self.client = APIClient()
        
    def test_schema_endpoint(self):
        response = self.client.get(
            "/api/schema/",
        )

        assert response.status_code == 200

    def test_swagger_endpoint(self):
        response = self.client.get(
            "/api/docs/",
        )

        assert response.status_code == 200