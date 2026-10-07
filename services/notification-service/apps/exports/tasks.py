from celery import shared_task
from .models import Export
from .services import ExportService

@shared_task(
    bind=True,
    name="apps.exports.tasks.generate_export",
)
def generate_export(
    self,
    export_id: str,
    rows: list[dict] | None = None,
):

    export = Export.objects.get(
        id=export_id,
    )

    rows = rows or []

    return ExportService.generate_export(
        export=export,
        rows=rows,
    ).id.hex