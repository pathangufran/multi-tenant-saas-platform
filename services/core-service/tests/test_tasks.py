import uuid
import pytest
from apps.common.exceptions import ResourceNotFoundError
from apps.projects.models import Project
from apps.tasks.models import Task
from apps.tasks.services import TaskService

@pytest.mark.django_db
class TestTaskService:

    def setup_method(self):
        self.tenant_id = uuid.uuid4()
        self.other_tenant_id = uuid.uuid4()
        self.user_id = uuid.uuid4()
        self.assignee_id = uuid.uuid4()
        self.tenant_a = uuid.uuid4()
        self.tenant_b = uuid.uuid4()

        self.project = Project.objects.create(
            tenant_id=self.tenant_id,
            name="Website Redesign",
            description="Website project",
            created_by=self.user_id,
        )

        self.project_a = Project.objects.create(
            tenant_id=self.tenant_a,
            name="Project A",
            created_by=self.user_id,
        )

        self.project_b = Project.objects.create(
            tenant_id=self.tenant_b,
            name="Project B",
            created_by=self.user_id,
        )

    def test_create_task(self):
        task = TaskService.create_task(
            tenant_id=self.tenant_id,
            project_id=self.project.id,
            user_id=self.user_id,
            title="Design landing page",
            description="Create responsive landing page",
            priority=Task.Priority.HIGH,
            assignee_id=self.assignee_id,
        )

        assert task.id is not None
        assert task.tenant_id == self.tenant_id
        assert task.project_id == self.project.id
        assert task.title == "Design landing page"
        assert task.description == "Create responsive landing page"
        assert task.priority == Task.Priority.HIGH
        assert task.status == Task.Status.TODO
        assert task.assignee_id == self.assignee_id
        assert task.created_by == self.user_id

    def test_create_task_defaults_to_medium_priority(self):
        task = TaskService.create_task(
            tenant_id=self.tenant_id,
            project_id=self.project.id,
            user_id=self.user_id,
            title="Create API",
        )

        assert task.priority == Task.Priority.MEDIUM
        assert task.status == Task.Status.TODO

    def test_create_task_with_due_date(self):
        due_date = "2026-10-15"

        task = TaskService.create_task(
            tenant_id=self.tenant_id,
            project_id=self.project.id,
            user_id=self.user_id,
            title="Release API",
            due_date=due_date,
        )

        assert str(task.due_date) == due_date

    def test_create_task_rejects_cross_tenant_project(self):
        with pytest.raises(ResourceNotFoundError):
            TaskService.create_task(
                tenant_id=self.other_tenant_id,
                project_id=self.project.id,
                user_id=self.user_id,
                title="Unauthorized Task",
            )

        assert not Task.objects.filter(
            title="Unauthorized Task",
        ).exists()

    def test_update_task(self):
        task = TaskService.create_task(
            tenant_id=self.tenant_id,
            project_id=self.project.id,
            user_id=self.user_id,
            title="Original Task",
        )

        updated_task = TaskService.update_task(
            tenant_id=self.tenant_id,
            task_id=task.id,
            data={
                "title": "Updated Task",
                "priority": Task.Priority.HIGH,
                "status": Task.Status.IN_PROGRESS,
            },
        )

        assert updated_task.title == "Updated Task"
        assert updated_task.priority == Task.Priority.HIGH
        assert updated_task.status == Task.Status.IN_PROGRESS

    def test_delete_task(self):
        task = TaskService.create_task(
            tenant_id=self.tenant_id,
            project_id=self.project.id,
            user_id=self.user_id,
            title="Delete Me",
        )

        TaskService.delete_task(
            tenant_id=self.tenant_id,
            task_id=task.id,
        )

        assert not Task.objects.filter(
            id=task.id,
        ).exists()

        self.project_a = Project.objects.create(
            tenant_id=self.tenant_a,
            name="Project A",
            created_by=self.user_id,
        )

        self.project_b = Project.objects.create(
            tenant_id=self.tenant_b,
            name="Project B",
            created_by=self.user_id,
        )

    def test_get_task(self):
        task = Task.objects.create(
            tenant_id=self.tenant_a,
            project_id=self.project_a.id,
            title="Task A",
            created_by=self.user_id,
        )

        result = TaskService.get_task(
            tenant_id=self.tenant_a,
            task_id=task.id,
        )

        assert result.id == task.id

    def test_cross_tenant_task_is_not_visible(self):
        task = Task.objects.create(
            tenant_id=self.tenant_a,
            project_id=self.project_a.id,
            title="Private Task",
            created_by=self.user_id,
        )

        with pytest.raises(ResourceNotFoundError):
            TaskService.get_task(
                tenant_id=self.tenant_b,
                task_id=task.id,
            )

    def test_list_project_tasks_is_tenant_scoped(self):
        task_a = Task.objects.create(
            tenant_id=self.tenant_a,
            project_id=self.project_a.id,
            title="Tenant A Task",
            created_by=self.user_id,
        )

        Task.objects.create(
            tenant_id=self.tenant_b,
            project_id=self.project_b.id,
            title="Tenant B Task",
            created_by=self.user_id,
        )

        tasks = TaskService.list_project_tasks(
            tenant_id=self.tenant_a,
            project_id=self.project_a.id,
        )

        task_ids = {
            task.id
            for task in tasks
        }

        assert task_a.id in task_ids
        assert len(task_ids) == 1

    def test_list_assigned_tasks(self):
        assignee_id = uuid.uuid4()

        assigned_task = Task.objects.create(
            tenant_id=self.tenant_a,
            project_id=self.project_a.id,
            title="Assigned Task",
            assignee_id=assignee_id,
            created_by=self.user_id,
        )

        Task.objects.create(
            tenant_id=self.tenant_a,
            project_id=self.project_a.id,
            title="Other Task",
            created_by=self.user_id,
        )

        tasks = TaskService.list_assigned_tasks(
            tenant_id=self.tenant_a,
            assignee_id=assignee_id,
        )

        task_ids = {
            task.id
            for task in tasks
        }

        assert assigned_task.id in task_ids
        assert len(task_ids) == 1

@pytest.mark.django_db
class TestTaskIsolation:

    def setup_method(self):
        self.tenant_a = uuid.uuid4()
        self.tenant_b = uuid.uuid4()
        self.user_id = uuid.uuid4()

        self.project = Project.objects.create(
            tenant_id=self.tenant_a,
            name="Tenant A Project",
            created_by=self.user_id,
        )

        self.task = Task.objects.create(
            tenant_id=self.tenant_a,
            project_id=self.project.id,
            title="Tenant A Task",
            created_by=self.user_id,
        )

    def test_cannot_update_other_tenant_task(self):
        with pytest.raises(ResourceNotFoundError):
            TaskService.update_task(
                tenant_id=self.tenant_b,
                task_id=self.task.id,
                data={
                    "title": "Hacked Task",
                },
            )

        self.task.refresh_from_db()

        assert self.task.title == "Tenant A Task"

    def test_cannot_delete_other_tenant_task(self):
        with pytest.raises(ResourceNotFoundError):
            TaskService.delete_task(
                tenant_id=self.tenant_b,
                task_id=self.task.id,
            )

        assert Task.objects.filter(
            id=self.task.id,
        ).exists()

    def test_cannot_create_task_under_other_tenant_project(self):
        with pytest.raises(ResourceNotFoundError):
            TaskService.create_task(
                tenant_id=self.tenant_b,
                project_id=self.project.id,
                user_id=self.user_id,
                title="Cross Tenant Task",
            )

        assert not Task.objects.filter(
            title="Cross Tenant Task",
        ).exists()