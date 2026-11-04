import uuid
import pytest
from apps.attachments.models import Attachment
from apps.attachments.services import AttachmentService
from apps.common.exceptions import ResourceNotFoundError
from apps.tasks.models import Task

@pytest.mark.django_db
class TestAttachmentService:

    def test_create_attachment(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_id,
            project_id=uuid.uuid4(),
            title="Test task",
            description="Test description",
            created_by=user_id,
        )

        attachment = AttachmentService.create_attachment(
            tenant_id=tenant_id,
            task_id=task.id,
            user_id=user_id,
            s3_key=f"tenants/{tenant_id}/tasks/{task.id}/file.pdf",
            filename="file.pdf",
            content_type="application/pdf",
            size=1024,
        )

        assert attachment.id is not None
        assert attachment.tenant_id == tenant_id
        assert attachment.task_id == task.id
        assert attachment.created_by == user_id
        assert attachment.filename == "file.pdf"
        assert attachment.content_type == "application/pdf"
        assert attachment.size == 1024

    def test_create_attachment_for_non_existing_task(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with pytest.raises(ResourceNotFoundError):
            AttachmentService.create_attachment(
                tenant_id=tenant_id,
                task_id=uuid.uuid4(),
                user_id=user_id,
                s3_key="file.pdf",
                filename="file.pdf",
                content_type="application/pdf",
                size=1024,
            )

    def test_create_attachment_for_other_tenant_task_fails(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_b,
            project_id=uuid.uuid4(),
            title="Tenant B task",
            created_by=user_id,
        )

        with pytest.raises(ResourceNotFoundError):
            AttachmentService.create_attachment(
                tenant_id=tenant_a,
                task_id=task.id,
                user_id=user_id,
                s3_key="file.pdf",
                filename="file.pdf",
                content_type="application/pdf",
                size=1024,
            )

    def test_delete_attachment(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_id,
            project_id=uuid.uuid4(),
            title="Test task",
            created_by=user_id,
        )

        attachment = Attachment.objects.create(
            tenant_id=tenant_id,
            task_id=task.id,
            s3_key="test/file.pdf",
            filename="file.pdf",
            content_type="application/pdf",
            size=2048,
            created_by=user_id,
        )

        AttachmentService.delete_attachment(
            tenant_id=tenant_id,
            attachment_id=attachment.id,
        )

        assert not Attachment.objects.filter(
            id=attachment.id,
        ).exists()

    def test_delete_cross_tenant_attachment_fails(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_b,
            project_id=uuid.uuid4(),
            title="Tenant B task",
            created_by=user_id,
        )

        attachment = Attachment.objects.create(
            tenant_id=tenant_b,
            task_id=task.id,
            s3_key="tenant-b/file.pdf",
            filename="file.pdf",
            content_type="application/pdf",
            size=2048,
            created_by=user_id,
        )

        with pytest.raises(ResourceNotFoundError):
            AttachmentService.delete_attachment(
                tenant_id=tenant_a,
                attachment_id=attachment.id,
            )

    def test_get_attachment(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_id,
            project_id=uuid.uuid4(),
            title="Test task",
            created_by=user_id,
        )

        attachment = Attachment.objects.create(
            tenant_id=tenant_id,
            task_id=task.id,
            s3_key="file.pdf",
            filename="file.pdf",
            content_type="application/pdf",
            size=1000,
            created_by=user_id,
        )

        result = AttachmentService.get_attachment(
            tenant_id=tenant_id,
            attachment_id=attachment.id,
        )

        assert result.id == attachment.id

    def test_get_attachment_cross_tenant_is_hidden(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_b,
            project_id=uuid.uuid4(),
            title="Tenant B task",
            created_by=user_id,
        )

        attachment = Attachment.objects.create(
            tenant_id=tenant_b,
            task_id=task.id,
            s3_key="tenant-b/file.pdf",
            filename="file.pdf",
            content_type="application/pdf",
            size=1000,
            created_by=user_id,
        )

        with pytest.raises(ResourceNotFoundError):
            AttachmentService.get_attachment(
                tenant_id=tenant_a,
                attachment_id=attachment.id,
            )

    def test_list_task_attachments(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_id,
            project_id=uuid.uuid4(),
            title="Test task",
            created_by=user_id,
        )

        first = Attachment.objects.create(
            tenant_id=tenant_id,
            task_id=task.id,
            s3_key="first.pdf",
            filename="first.pdf",
            content_type="application/pdf",
            size=100,
            created_by=user_id,
        )

        second = Attachment.objects.create(
            tenant_id=tenant_id,
            task_id=task.id,
            s3_key="second.pdf",
            filename="second.pdf",
            content_type="application/pdf",
            size=200,
            created_by=user_id,
        )

        attachments = AttachmentService.list_task_attachments(
            tenant_id=tenant_id,
            task_id=task.id,
        )

        assert list(attachments) == [second, first]

    def test_list_task_attachments_is_tenant_scoped(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()

        task_a = Task.objects.create(
            tenant_id=tenant_a,
            project_id=uuid.uuid4(),
            title="Tenant A task",
            created_by=uuid.uuid4(),
        )

        task_b = Task.objects.create(
            tenant_id=tenant_b,
            project_id=uuid.uuid4(),
            title="Tenant B task",
            created_by=uuid.uuid4(),
        )

        Attachment.objects.create(
            tenant_id=tenant_a,
            task_id=task_a.id,
            s3_key="tenant-a/file.pdf",
            filename="file.pdf",
            content_type="application/pdf",
            size=100,
            created_by=uuid.uuid4(),
        )

        Attachment.objects.create(
            tenant_id=tenant_b,
            task_id=task_b.id,
            s3_key="tenant-b/file.pdf",
            filename="file.pdf",
            content_type="application/pdf",
            size=100,
            created_by=uuid.uuid4(),
        )

        attachments = AttachmentService.list_task_attachments(
            tenant_id=tenant_a,
            task_id=task_b.id,
        )

        assert attachments.count() == 0

    def test_list_user_attachments(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_id,
            project_id=uuid.uuid4(),
            title="Test task",
            created_by=user_id,
        )

        Attachment.objects.create(
            tenant_id=tenant_id,
            task_id=task.id,
            s3_key="first.pdf",
            filename="first.pdf",
            content_type="application/pdf",
            size=100,
            created_by=user_id,
        )

        Attachment.objects.create(
            tenant_id=tenant_id,
            task_id=task.id,
            s3_key="second.pdf",
            filename="second.pdf",
            content_type="application/pdf",
            size=200,
            created_by=user_id,
        )

        attachments = AttachmentService.list_user_attachments(
            tenant_id=tenant_id,
            user_id=user_id,
        )

        assert attachments.count() == 2

@pytest.mark.django_db
class TestAttachmentModel:

    def test_attachment_stores_metadata(self):
        tenant_id = uuid.uuid4()
        task_id = uuid.uuid4()
        user_id = uuid.uuid4()

        attachment = Attachment.objects.create(
            tenant_id=tenant_id,
            task_id=task_id,
            s3_key="tenants/test/tasks/test/report.pdf",
            filename="report.pdf",
            content_type="application/pdf",
            size=4096,
            created_by=user_id,
        )

        assert attachment.s3_key.endswith("report.pdf")
        assert attachment.filename == "report.pdf"
        assert attachment.content_type == "application/pdf"
        assert attachment.size == 4096

    def test_multiple_attachments_can_exist_for_same_task(self):
        tenant_id = uuid.uuid4()
        task_id = uuid.uuid4()
        user_id = uuid.uuid4()

        Attachment.objects.create(
            tenant_id=tenant_id,
            task_id=task_id,
            s3_key="file-1.pdf",
            filename="file-1.pdf",
            content_type="application/pdf",
            size=100,
            created_by=user_id,
        )

        Attachment.objects.create(
            tenant_id=tenant_id,
            task_id=task_id,
            s3_key="file-2.png",
            filename="file-2.png",
            content_type="image/png",
            size=200,
            created_by=user_id,
        )

        assert Attachment.objects.filter(
            tenant_id=tenant_id,
            task_id=task_id,
        ).count() == 2