import uuid
import pytest
from django.core.files.storage import default_storage
from apps.exports.models import Export
from apps.exports.tasks import generate_export

@pytest.mark.django_db
class TestGenerateExportTask:

    def test_generates_export(self):

        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        export = Export.objects.create(
            tenant_id=tenant_id,
            requested_by=user_id,
            export_type=Export.ExportType.PROJECTS,
        )

        rows = [
            {
                "id": "1",
                "name": "Project A",
            },
            {
                "id": "2",
                "name": "Project B",
            },
        ]

        result = generate_export.apply(
            args=[
                str(export.id),
                rows,
            ],
        ).get()

        export.refresh_from_db()

        assert result == export.id.hex

        assert (
            export.status
            == Export.Status.COMPLETED
        )

        assert export.row_count == 2
        assert export.storage_key

        assert default_storage.exists(
            export.storage_key,
        )

        default_storage.delete(
            export.storage_key,
        )

    def test_generates_empty_export(self):

        export = Export.objects.create(
            tenant_id=uuid.uuid4(),
            requested_by=uuid.uuid4(),
            export_type=Export.ExportType.TASKS,
        )

        generate_export.apply(
            args=[
                str(export.id),
                [],
            ],
        ).get()

        export.refresh_from_db()

        assert (
            export.status
            == Export.Status.COMPLETED
        )

        assert export.row_count == 0

        default_storage.delete(
            export.storage_key,
        )