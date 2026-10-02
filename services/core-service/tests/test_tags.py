import uuid
import pytest
from apps.common.exceptions import ConflictError, ResourceNotFoundError
from apps.tags.models import Tag, TaskTag
from apps.tags.services import TagService
from apps.tasks.models import Task

@pytest.mark.django_db
class TestTagService:

    def test_create_tag(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        tag = TagService.create_tag(
            tenant_id=tenant_id,
            user_id=user_id,
            name="Backend",
        )

        assert tag.id is not None
        assert tag.tenant_id == tenant_id
        assert tag.name == "Backend"
        assert tag.created_by == user_id

    def test_duplicate_tag_name_same_tenant_fails(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        TagService.create_tag(
            tenant_id=tenant_id,
            user_id=user_id,
            name="Backend",
        )

        with pytest.raises(ConflictError):
            TagService.create_tag(
                tenant_id=tenant_id,
                user_id=user_id,
                name="Backend",
            )

    def test_same_tag_name_allowed_for_different_tenants(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()

        tag_a = TagService.create_tag(
            tenant_id=tenant_a,
            user_id=uuid.uuid4(),
            name="Backend",
        )

        tag_b = TagService.create_tag(
            tenant_id=tenant_b,
            user_id=uuid.uuid4(),
            name="Backend",
        )

        assert tag_a.name == tag_b.name
        assert tag_a.tenant_id != tag_b.tenant_id

    def test_update_tag(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        tag = TagService.create_tag(
            tenant_id=tenant_id,
            user_id=user_id,
            name="Backend",
        )

        updated = TagService.update_tag(
            tenant_id=tenant_id,
            tag_id=tag.id,
            name="Python",
        )

        updated.refresh_from_db()

        assert updated.name == "Python"

    def test_update_cross_tenant_tag_fails(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()

        tag = TagService.create_tag(
            tenant_id=tenant_b,
            user_id=uuid.uuid4(),
            name="Backend",
        )

        with pytest.raises(ResourceNotFoundError):
            TagService.update_tag(
                tenant_id=tenant_a,
                tag_id=tag.id,
                name="Unauthorized",
            )

    def test_delete_tag(self):
        tenant_id = uuid.uuid4()

        tag = TagService.create_tag(
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            name="Backend",
        )

        TagService.delete_tag(
            tenant_id=tenant_id,
            tag_id=tag.id,
        )

        assert not Tag.objects.filter(
            id=tag.id,
        ).exists()

    def test_delete_cross_tenant_tag_fails(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()

        tag = TagService.create_tag(
            tenant_id=tenant_b,
            user_id=uuid.uuid4(),
            name="Backend",
        )

        with pytest.raises(ResourceNotFoundError):
            TagService.delete_tag(
                tenant_id=tenant_a,
                tag_id=tag.id,
            )

    def test_attach_tag_to_task(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_id,
            project_id=uuid.uuid4(),
            title="Build API",
            created_by=user_id,
        )

        tag = TagService.create_tag(
            tenant_id=tenant_id,
            user_id=user_id,
            name="Backend",
        )

        task_tag = TagService.attach_tag_to_task(
            tenant_id=tenant_id,
            task_id=task.id,
            tag_id=tag.id,
        )

        assert task_tag.id is not None
        assert task_tag.tenant_id == tenant_id
        assert task_tag.task_id == task.id
        assert task_tag.tag_id == tag.id

    def test_attach_non_existing_task_fails(self):
        tenant_id = uuid.uuid4()

        tag = TagService.create_tag(
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            name="Backend",
        )

        with pytest.raises(ResourceNotFoundError):
            TagService.attach_tag_to_task(
                tenant_id=tenant_id,
                task_id=uuid.uuid4(),
                tag_id=tag.id,
            )

    def test_attach_cross_tenant_task_fails(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_b,
            project_id=uuid.uuid4(),
            title="Tenant B task",
            created_by=uuid.uuid4(),
        )

        tag = TagService.create_tag(
            tenant_id=tenant_a,
            user_id=uuid.uuid4(),
            name="Backend",
        )

        with pytest.raises(ResourceNotFoundError):
            TagService.attach_tag_to_task(
                tenant_id=tenant_a,
                task_id=task.id,
                tag_id=tag.id,
            )

    def test_attach_cross_tenant_tag_fails(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_a,
            project_id=uuid.uuid4(),
            title="Tenant A task",
            created_by=uuid.uuid4(),
        )

        tag = TagService.create_tag(
            tenant_id=tenant_b,
            user_id=uuid.uuid4(),
            name="Backend",
        )

        with pytest.raises(ResourceNotFoundError):
            TagService.attach_tag_to_task(
                tenant_id=tenant_a,
                task_id=task.id,
                tag_id=tag.id,
            )

    def test_duplicate_tag_attachment_fails(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_id,
            project_id=uuid.uuid4(),
            title="Build API",
            created_by=user_id,
        )

        tag = TagService.create_tag(
            tenant_id=tenant_id,
            user_id=user_id,
            name="Backend",
        )

        TagService.attach_tag_to_task(
            tenant_id=tenant_id,
            task_id=task.id,
            tag_id=tag.id,
        )

        with pytest.raises(ConflictError):
            TagService.attach_tag_to_task(
                tenant_id=tenant_id,
                task_id=task.id,
                tag_id=tag.id,
            )

    def test_remove_tag_from_task(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_id,
            project_id=uuid.uuid4(),
            title="Build API",
            created_by=user_id,
        )

        tag = TagService.create_tag(
            tenant_id=tenant_id,
            user_id=user_id,
            name="Backend",
        )

        TagService.attach_tag_to_task(
            tenant_id=tenant_id,
            task_id=task.id,
            tag_id=tag.id,
        )

        TagService.remove_tag_from_task(
            tenant_id=tenant_id,
            task_id=task.id,
            tag_id=tag.id,
        )

        assert not TaskTag.objects.filter(
            tenant_id=tenant_id,
            task_id=task.id,
            tag_id=tag.id,
        ).exists()

    def test_remove_cross_tenant_tag_attachment_fails(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_b,
            project_id=uuid.uuid4(),
            title="Tenant B task",
            created_by=uuid.uuid4(),
        )

        tag = TagService.create_tag(
            tenant_id=tenant_b,
            user_id=uuid.uuid4(),
            name="Backend",
        )

        TagService.attach_tag_to_task(
            tenant_id=tenant_b,
            task_id=task.id,
            tag_id=tag.id,
        )

        with pytest.raises(ResourceNotFoundError):
            TagService.remove_tag_from_task(
                tenant_id=tenant_a,
                task_id=task.id,
                tag_id=tag.id,
            )

    def test_get_tag(self):
        tenant_id = uuid.uuid4()

        tag = TagService.create_tag(
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            name="Backend",
        )

        result = TagService.get_tag(
            tenant_id=tenant_id,
            tag_id=tag.id,
        )

        assert result.id == tag.id

    def test_get_tag_is_tenant_scoped(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()

        tag = TagService.create_tag(
            tenant_id=tenant_b,
            user_id=uuid.uuid4(),
            name="Backend",
        )

        with pytest.raises(ResourceNotFoundError):
            TagService.get_tag(
                tenant_id=tenant_a,
                tag_id=tag.id,
            )

    def test_list_tags(self):
        tenant_id = uuid.uuid4()

        TagService.create_tag(
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            name="Backend",
        )

        TagService.create_tag(
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            name="Frontend",
        )

        tags = TagService.list_tags(
            tenant_id=tenant_id,
        )

        assert [tag.name for tag in tags] == [
            "Backend",
            "Frontend",
        ]

    def test_list_tags_does_not_return_other_tenant(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()

        TagService.create_tag(
            tenant_id=tenant_a,
            user_id=uuid.uuid4(),
            name="Backend",
        )

        TagService.create_tag(
            tenant_id=tenant_b,
            user_id=uuid.uuid4(),
            name="Frontend",
        )

        tags = TagService.list_tags(
            tenant_id=tenant_a,
        )

        assert tags.count() == 1
        assert tags.first().name == "Backend"

    def test_list_task_tags(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_id,
            project_id=uuid.uuid4(),
            title="Build API",
            created_by=user_id,
        )

        backend = TagService.create_tag(
            tenant_id=tenant_id,
            user_id=user_id,
            name="Backend",
        )

        frontend = TagService.create_tag(
            tenant_id=tenant_id,
            user_id=user_id,
            name="Frontend",
        )

        TagService.attach_tag_to_task(
            tenant_id=tenant_id,
            task_id=task.id,
            tag_id=backend.id,
        )

        TagService.attach_tag_to_task(
            tenant_id=tenant_id,
            task_id=task.id,
            tag_id=frontend.id,
        )

        tags = TagService.list_task_tags(
            tenant_id=tenant_id,
            task_id=task.id,
        )

        assert [tag.name for tag in tags] == [
            "Backend",
            "Frontend",
        ]

    def test_list_task_tags_is_tenant_scoped(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_b,
            project_id=uuid.uuid4(),
            title="Tenant B task",
            created_by=uuid.uuid4(),
        )

        tag = TagService.create_tag(
            tenant_id=tenant_b,
            user_id=uuid.uuid4(),
            name="Backend",
        )

        TagService.attach_tag_to_task(
            tenant_id=tenant_b,
            task_id=task.id,
            tag_id=tag.id,
        )

        tags = TagService.list_task_tags(
            tenant_id=tenant_a,
            task_id=task.id,
        )

        assert tags.count() == 0