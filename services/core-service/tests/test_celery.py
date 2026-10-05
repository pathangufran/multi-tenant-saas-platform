import os
from celery import current_app

class TestCeleryConfiguration:

    def test_celery_application_is_configured(self):
        assert current_app.main == "core_service"

    def test_celery_broker_url_is_configured(self):
        broker_url = current_app.conf.broker_url

        assert broker_url
        assert broker_url.startswith("redis://")

    def test_celery_result_backend_is_configured(self):
        result_backend = current_app.conf.result_backend

        assert result_backend
        assert result_backend.startswith("redis://")

    def test_celery_broker_environment_variable_exists(self):
        assert os.getenv("CELERY_BROKER_URL")

    def test_celery_result_backend_environment_variable_exists(self):
        assert os.getenv("CELERY_RESULT_BACKEND")