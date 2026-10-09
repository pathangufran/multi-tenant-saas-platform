import uuid
import pytest
from apps.exports.models import Export
from apps.exports.services import ExportService

@pytest.mark.django_db
class TestExportAPI:

    def setup_method(self):

        self.tenant_id = uuid.uuid4()
        self.other_tenant_id = uuid.uuid4()

        self.user_id = uuid.uuid4()

    def test_tenant_can_create_export_record(
        self,
    ):

        export = ExportService.create_export(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            export_type=Export.ExportType.PROJECTS,
        )

        assert export.tenant_id == self.tenant_id
        assert export.requested_by == self.user_id

    def test_other_tenant_cannot_access_export(
        self,
    ):

        export = Export.objects.create(
            tenant_id=self.other_tenant_id,
            requested_by=uuid.uuid4(),
            export_type=Export.ExportType.PROJECTS,
        )

        with pytest.raises(
            ValueError,match="Export not found"
        ):
            ExportService.get_export(
                tenant_id=self.tenant_id,
                export_id=export.id,
            )

    def test_other_tenant_cannot_download_export(
        self,
    ):

        export = Export.objects.create(
            tenant_id=self.other_tenant_id,
            requested_by=uuid.uuid4(),
            export_type=Export.ExportType.PROJECTS,
        )

        with pytest.raises(
            ValueError,match="Export not found"
        ):
            ExportService.get_export(
                tenant_id=self.tenant_id,
                export_id=export.id,
            )

    def test_pending_export_cannot_download(
        self,
    ):

        export = Export.objects.create(
            tenant_id=self.tenant_id,
            requested_by=self.user_id,
            export_type=Export.ExportType.TASKS,
        )

        with pytest.raises(
            ValueError,
            match="not ready",
        ):
            ExportService.get_download_url(
                export=export,
            )