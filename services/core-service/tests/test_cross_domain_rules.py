import uuid
import pytest
from apps.common.domain_rules import CoreDomainRules
from apps.common.exceptions import ResourceNotFoundError
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.tags.models import Tag, TaskTag

@pytest.mark.django_db
class TestCoreDomainRules:
    def _tenant(self):
        return uuid.uuid4()

    def _user(self):
        return uuid.uuid4()

    def _project(self, tenant_id):
        return Project.objects.create(
            tenant_id=tenant_id,
            name=f"Project-{uuid.uuid4().hex[:8]}",
            description="test project",
            created_by=self._user(),
        )

    def _task(self, tenant_id, project_id):
        return Task.objects.create(
            tenant_id=tenant_id,
            project_id=project_id,
            title=f"Task-{uuid.uuid4().hex[:8]}",
            description="test task",
            priority=Task.Priority.MEDIUM,
            status=Task.Status.TODO,
            created_by=self._user(),
        )

    def _tag(self, tenant_id):
        return Tag.objects.create(
            tenant_id=tenant_id,
            name=f"Tag-{uuid.uuid4().hex[:8]}",
            created_by=self._user(),
        )

    def test_project_must_belong_to_current_tenant(self):
        tenant_a = self._tenant()
        tenant_b = self._tenant()
        project = self._project(tenant_a)

        assert CoreDomainRules.ensure_project_belongs_to_tenant(
            tenant_id=tenant_a,
            project_id=project.id,
        ) == project

        with pytest.raises(ResourceNotFoundError, match="Project not found"):
            CoreDomainRules.ensure_project_belongs_to_tenant(
                tenant_id=tenant_b,
                project_id=project.id,
            )

    def test_task_must_belong_to_current_tenant(self):
        tenant_a = self._tenant()
        tenant_b = self._tenant()
        project = self._project(tenant_a)
        task = self._task(tenant_a, project.id)

        assert CoreDomainRules.ensure_task_belongs_to_tenant(
            tenant_id=tenant_a,
            task_id=task.id,
        ) == task

        with pytest.raises(ResourceNotFoundError, match="Task not found"):
            CoreDomainRules.ensure_task_belongs_to_tenant(
                tenant_id=tenant_b,
                task_id=task.id,
            )

    def test_task_must_belong_to_specified_project(self):
        tenant_id = self._tenant()
        project_a = self._project(tenant_id)
        project_b = self._project(tenant_id)
        task = self._task(tenant_id, project_a.id)

        assert CoreDomainRules.ensure_task_belongs_to_project(
            tenant_id=tenant_id,
            task_id=task.id,
            project_id=project_a.id,
        ) == task

        with pytest.raises(
            ResourceNotFoundError,
            match="Task does not belong to the specified project",
        ):
            CoreDomainRules.ensure_task_belongs_to_project(
                tenant_id=tenant_id,
                task_id=task.id,
                project_id=project_b.id,
            )

    def test_tag_must_belong_to_current_tenant(self):
        tenant_a = self._tenant()
        tenant_b = self._tenant()
        tag = self._tag(tenant_a)

        assert CoreDomainRules.ensure_tag_belongs_to_tenant(
            tenant_id=tenant_a,
            tag_id=tag.id,
        ) == tag

        with pytest.raises(ResourceNotFoundError, match="Tag not found"):
            CoreDomainRules.ensure_tag_belongs_to_tenant(
                tenant_id=tenant_b,
                tag_id=tag.id,
            )

    def test_task_tag_must_match_tenant_and_tag_tenant(self):
        tenant_a = self._tenant()
        tenant_b = self._tenant()
        project = self._project(tenant_a)
        task = self._task(tenant_a, project.id)
        tag = self._tag(tenant_a)

        task_tag = TaskTag.objects.create(
            tenant_id=tenant_a,
            task_id=task.id,
            tag=tag,
        )

        assert CoreDomainRules.ensure_task_tag_belongs_to_tenant(
            tenant_id=tenant_a,
            task_tag_id=task_tag.id,
        ) == task_tag

        with pytest.raises(ResourceNotFoundError, match="Task tag not found"):
            CoreDomainRules.ensure_task_tag_belongs_to_tenant(
                tenant_id=tenant_b,
                task_tag_id=task_tag.id,
            )

    def test_task_and_tag_must_belong_to_same_tenant(self):
        tenant_a = self._tenant()
        tenant_b = self._tenant()
        project = self._project(tenant_a)
        task = self._task(tenant_a, project.id)
        tag = self._tag(tenant_a)

        result_task, result_tag = CoreDomainRules.ensure_task_and_tag_same_tenant(
            tenant_id=tenant_a,
            task_id=task.id,
            tag_id=tag.id,
        )

        assert result_task == task
        assert result_tag == tag

        foreign_tag = self._tag(tenant_b)
        with pytest.raises(ResourceNotFoundError, match="Tag not found"):
            CoreDomainRules.ensure_task_and_tag_same_tenant(
                tenant_id=tenant_a,
                task_id=task.id,
                tag_id=foreign_tag.id,
            )

    def test_same_tenant_rule_accepts_matching_tenants(self):
        tenant_id = self._tenant()

        CoreDomainRules.ensure_same_tenant(
            tenant_id=tenant_id,
            resource_tenant_id=tenant_id,
        )

    def test_same_tenant_rule_rejects_cross_tenant_resource(self):
        with pytest.raises(ResourceNotFoundError, match="Resource not found"):
            CoreDomainRules.ensure_same_tenant(
                tenant_id=self._tenant(),
                resource_tenant_id=self._tenant(),
            )

    def test_missing_project_is_not_exposed_across_tenants(self):
        tenant_id = self._tenant()

        with pytest.raises(ResourceNotFoundError, match="Project not found"):
            CoreDomainRules.ensure_project_belongs_to_tenant(
                tenant_id=tenant_id,
                project_id=uuid.uuid4(),
            )

    def test_missing_task_is_not_exposed_across_tenants(self):
        tenant_id = self._tenant()

        with pytest.raises(ResourceNotFoundError, match="Task not found"):
            CoreDomainRules.ensure_task_belongs_to_tenant(
                tenant_id=tenant_id,
                task_id=uuid.uuid4(),
            )

    def test_missing_tag_is_not_exposed_across_tenants(self):
        tenant_id = self._tenant()

        with pytest.raises(ResourceNotFoundError, match="Tag not found"):
            CoreDomainRules.ensure_tag_belongs_to_tenant(
                tenant_id=tenant_id,
                tag_id=uuid.uuid4(),
            )


@pytest.mark.django_db
class TestCoreDomainServiceIntegration:
    def _tenant(self):
        return uuid.uuid4()

    def _user(self):
        return uuid.uuid4()

    def _project(self, tenant_id):
        return Project.objects.create(
            tenant_id=tenant_id,
            name=f"Project-{uuid.uuid4().hex[:8]}",
            description="test project",
            created_by=self._user(),
        )

    def _task(self, tenant_id, project_id):
        return Task.objects.create(
            tenant_id=tenant_id,
            project_id=project_id,
            title=f"Task-{uuid.uuid4().hex[:8]}",
            priority=Task.Priority.MEDIUM,
            status=Task.Status.TODO,
            created_by=self._user(),
        )

    def _tag(self, tenant_id):
        return Tag.objects.create(
            tenant_id=tenant_id,
            name=f"Tag-{uuid.uuid4().hex[:8]}",
            created_by=self._user(),
        )

    def test_task_project_listing_rejects_foreign_project(self):
        from apps.tasks.services import TaskService

        tenant_a = self._tenant()
        tenant_b = self._tenant()
        project = self._project(tenant_a)

        with pytest.raises(ResourceNotFoundError, match="Project not found"):
            TaskService.list_project_tasks(
                tenant_id=tenant_b,
                project_id=project.id,
            )

    def test_comment_listing_rejects_foreign_task(self):
        from apps.comments.services import CommentService

        tenant_a = self._tenant()
        tenant_b = self._tenant()
        project = self._project(tenant_a)
        task = self._task(tenant_a, project.id)

        with pytest.raises(ResourceNotFoundError, match="Task not found"):
            CommentService.list_task_comments(
                tenant_id=tenant_b,
                task_id=task.id,
            )

    def test_attachment_listing_rejects_foreign_task(self):
        from apps.attachments.services import AttachmentService

        tenant_a = self._tenant()
        tenant_b = self._tenant()
        project = self._project(tenant_a)
        task = self._task(tenant_a, project.id)

        with pytest.raises(ResourceNotFoundError, match="Task not found"):
            AttachmentService.list_task_attachments(
                tenant_id=tenant_b,
                task_id=task.id,
            )

    def test_tag_listing_rejects_foreign_task(self):
        from apps.tags.services import TagService

        tenant_a = self._tenant()
        tenant_b = self._tenant()
        project = self._project(tenant_a)
        task = self._task(tenant_a, project.id)

        with pytest.raises(ResourceNotFoundError, match="Task not found"):
            TagService.list_task_tags(
                tenant_id=tenant_b,
                task_id=task.id,
            )

    def test_tag_attachment_rejects_cross_tenant_tag(self):
        from apps.tags.services import TagService

        tenant_a = self._tenant()
        tenant_b = self._tenant()
        project = self._project(tenant_a)
        task = self._task(tenant_a, project.id)
        foreign_tag = self._tag(tenant_b)

        with pytest.raises(ResourceNotFoundError, match="Tag not found"):
            TagService.attach_tag_to_task(
                tenant_id=tenant_a,
                task_id=task.id,
                tag_id=foreign_tag.id,
            )

    def test_tag_attachment_rejects_cross_tenant_task(self):
        from apps.tags.services import TagService

        tenant_a = self._tenant()
        tenant_b = self._tenant()
        project = self._project(tenant_a)
        task = self._task(tenant_a, project.id)
        tag = self._tag(tenant_b)

        with pytest.raises(ResourceNotFoundError, match="Task not found"):
            TagService.attach_tag_to_task(
                tenant_id=tenant_b,
                task_id=task.id,
                tag_id=tag.id,
            )

    def test_task_tag_lookup_is_tenant_scoped(self):
        from apps.tags.services import TagService

        tenant_a = self._tenant()
        tenant_b = self._tenant()
        project = self._project(tenant_a)
        task = self._task(tenant_a, project.id)
        tag = self._tag(tenant_a)

        task_tag = TaskTag.objects.create(
            tenant_id=tenant_a,
            task_id=task.id,
            tag=tag,
        )

        with pytest.raises(ResourceNotFoundError, match="TaskTag not found"):
            TagService.get_task_tag(
                tenant_id=tenant_b,
                task_id=task.id,
                tag_id=tag.id,
            )

        assert TagService.get_task_tag(
            tenant_id=tenant_a,
            task_id=task.id,
            tag_id=tag.id,
        ) == task_tag
