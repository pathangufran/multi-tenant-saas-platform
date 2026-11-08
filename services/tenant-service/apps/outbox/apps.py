from django.apps import AppConfig

class OutboxConfig(AppConfig):
    default_auto_field = 'django_db.models.BigAutoField'
    name = 'apps.outbox'
    label = 'outbox'
    verbose_name = 'Outbox'