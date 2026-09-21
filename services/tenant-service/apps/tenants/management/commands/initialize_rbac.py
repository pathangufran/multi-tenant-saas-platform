from django.core.management.base import BaseCommand
from apps.tenants.rbac_service import RBACService

class Command(BaseCommand):
    help = "Initialize default RBAC permissions."

    def handle(self, *args, **options):
        permissions = RBACService.initialize_permissions()

        self.stdout.write(
            self.style.SUCCESS(
                "RBAC initialization completed."
            )
        )

        self.stdout.write(
            f"Permissions initialized: {len(permissions)}"
        )