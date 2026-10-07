import uuid
import pytest
from django.core.files.storage import default_storage
from apps.exports.models import Export
from apps.exports.services import ExportService

@pytest.mark.django_db
class TestExportService:

    def setup_method(self):

        self.tenant_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

    def test_create_export(self):

        export = ExportService.create_export(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            export_type=Export.ExportType.PROJECTS,
        )

        assert export.tenant_id == self.tenant_id
        assert export.requested_by == self.user_id
        assert (
            export.export_type
            == Export.ExportType.PROJECTS
        )
        assert (
            export.status
            == Export.Status.PENDING
        )

    def test_create_export_rejects_invalid_type(self):

        with pytest.raises(
            ValueError,
            match="Unsupported export type",
        ):
            ExportService.create_export(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                export_type="INVALID",
            )

    def test_build_csv(self):

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

        content, row_count = (
            ExportService.build_csv(
                rows=rows,
            )
        )

        csv_content = content.decode(
            "utf-8",
        )

        assert "id,name" in csv_content
        assert "1,Project A" in csv_content
        assert "2,Project B" in csv_content
        assert row_count == 2

    def test_build_csv_with_empty_rows(self):

        content, row_count = (
            ExportService.build_csv(
                rows=[],
            )
        )

        csv_content = content.decode(
            "utf-8",
        )

        assert "message" in csv_content
        assert "No records found" in csv_content
        assert row_count == 0

    def test_mark_processing(self):

        export = Export.objects.create(
            tenant_id=self.tenant_id,
            requested_by=self.user_id,
            export_type=Export.ExportType.TASKS,
        )

        ExportService.mark_processing(
            export=export,
        )

        export.refresh_from_db()

        assert (
            export.status
            == Export.Status.PROCESSING
        )

    def test_generate_export_completes_export(
        self,
    ):

        export = Export.objects.create(
            tenant_id=self.tenant_id,
            requested_by=self.user_id,
            export_type=Export.ExportType.PROJECTS,
        )

        rows = [
            {
                "id": "project-1",
                "name": "Project A",
            },
            {
                "id": "project-2",
                "name": "Project B",
            },
        ]

        result = ExportService.generate_export(
            export=export,
            rows=rows,
        )

        result.refresh_from_db()

        assert (
            result.status
            == Export.Status.COMPLETED
        )

        assert result.row_count == 2
        assert result.file_name
        assert result.storage_key
        assert result.completed_at is not None

        assert default_storage.exists(
            result.storage_key,
        )

        default_storage.delete(
            result.storage_key,
        )

    def test_generate_export_empty_data(
        self,
    ):

        export = Export.objects.create(
            tenant_id=self.tenant_id,
            requested_by=self.user_id,
            export_type=Export.ExportType.USERS,
        )

        result = ExportService.generate_export(
            export=export,
            rows=[],
        )

        result.refresh_from_db()

        assert (
            result.status
            == Export.Status.COMPLETED
        )

        assert result.row_count == 0
        assert result.storage_key

        default_storage.delete(
            result.storage_key,
        )

    def test_get_export_is_tenant_scoped(
        self,
    ):

        export = Export.objects.create(
            tenant_id=self.tenant_id,
            requested_by=self.user_id,
            export_type=Export.ExportType.TASKS,
        )

        other_tenant = uuid.uuid4()

        with pytest.raises(
            Export.DoesNotExist,
        ):
            ExportService.get_export(
                tenant_id=other_tenant,
                export_id=export.id,
            )

    def test_list_exports_is_tenant_scoped(
        self,
    ):

        other_tenant = uuid.uuid4()

        Export.objects.create(
            tenant_id=self.tenant_id,
            requested_by=self.user_id,
            export_type=Export.ExportType.PROJECTS,
        )

        Export.objects.create(
            tenant_id=other_tenant,
            requested_by=uuid.uuid4(),
            export_type=Export.ExportType.PROJECTS,
        )

        exports = ExportService.list_exports(
            tenant_id=self.tenant_id,
        )

        assert exports.count() == 1

        assert (
            exports.first().tenant_id
            == self.tenant_id
        )

    def test_download_url_requires_completed_export(
        self,
    ):

        export = Export.objects.create(
            tenant_id=self.tenant_id,
            requested_by=self.user_id,
            export_type=Export.ExportType.AUDIT_LOGS,
        )

        with pytest.raises(
            ValueError,
            match="not ready",
        ):
            ExportService.get_download_url(
                export=export,
            )