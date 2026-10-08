from django.apps import AppConfig


class FailedJobsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.failed_jobs'
    verbose_name = "Failed Jobs"
