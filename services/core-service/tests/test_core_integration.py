import uuid
import pytest
from apps.common.exceptions import ResourceNotFoundError
from apps.projects.models import Project
from apps.projects.services import ProjectService
from apps.teams.models import Team
from apps.teams.services import TeamService
from apps.tasks.models import Task
from apps.tasks.services import TaskService
from apps.comments.models import Comment
from apps.comments.services import CommentService
from apps.attachments.models import Attachment
from apps.attachments.services import AttachmentService
from apps.tags.models import Tag, TaskTag
from apps.tags.services import TagService

@pytest.mark.django_db
class TestCoreServiceIntegration:

    def setup_method(self):
        self.tenant_a = uuid.uuid4()
        self.tenant_b = uuid.uuid4()
        self.user_a = uuid.uuid4()
        self.user_b = uuid.uuid4()

    def test_complete_core_domain_workflow(self):
        """
        Validate the complete Core Service domain relationship:

        Tenant
            -> Team
            -> Project
                -> Task
                    -> Comment
                    -> Attachment
                    -> Tag
        """

        # ---------------------------------------------------------
        # 1. Team
        # ---------------------------------------------------------

        team = TeamService.create_team(
            tenant_id=self.tenant_a,
            user_id=self.user_a,
            name="Engineering",
            description="Engineering team",
        )

        assert team.tenant_id == self.tenant_a

        # ---------------------------------------------------------
        # 2. Project
        # ---------------------------------------------------------

        project = ProjectService.create_project(
            tenant_id=self.tenant_a,
            user_id=self.user_a,
            name="Website Redesign",
            description="Redesign company website",
        )

        assert project.tenant_id == self.tenant_a
        assert project.created_by == self.user_a

        # ---------------------------------------------------------
        # 3. Task
        # ---------------------------------------------------------

        task = TaskService.create_task(
            tenant_id=self.tenant_a,
            project_id=project.id,
            user_id=self.user_a,
            title="Design landing page",
            description="Create responsive landing page",
            priority=Task.Priority.HIGH,
            assignee_id=self.user_a,
        )

        assert task.tenant_id == self.tenant_a
        assert task.project_id == project.id
        assert task.created_by == self.user_a

        # ---------------------------------------------------------
        # 4. Comment
        # ---------------------------------------------------------

        comment = CommentService.create_comment(
            tenant_id=self.tenant_a,
            task_id=task.id,
            user_id=self.user_a,
            content={"text": "Started working on the landing page."},
        )

        assert comment.tenant_id == self.tenant_a
        assert comment.task_id == task.id
        assert comment.created_by == self.user_a

        # ---------------------------------------------------------
        # 5. Attachment
        # ---------------------------------------------------------

        attachment = AttachmentService.create_attachment(
            tenant_id=self.tenant_a,
            task_id=task.id,
            user_id=self.user_a,
            s3_key="tenant-a/tasks/landing-page/design.pdf",
            filename="design.pdf",
            content_type="application/pdf",
            size=1024,
        )

        assert attachment.tenant_id == self.tenant_a
        assert attachment.task_id == task.id
        assert attachment.created_by == self.user_a

        # ---------------------------------------------------------
        # 6. Tag
        # ---------------------------------------------------------

        tag = TagService.create_tag(
            tenant_id=self.tenant_a,
            user_id=self.user_a,
            name="Frontend",
        )

        assert tag.tenant_id == self.tenant_a

        # ---------------------------------------------------------
        # 7. Attach Tag -> Task
        # ---------------------------------------------------------

        task_tag = TagService.attach_tag_to_task(
            tenant_id=self.tenant_a,
            task_id=task.id,
            tag_id=tag.id,
        )

        assert task_tag.tenant_id == self.tenant_a
        assert task_tag.task_id == task.id
        assert task_tag.tag_id == tag.id

        # ---------------------------------------------------------
        # 8. Verify complete relationship
        # ---------------------------------------------------------

        assert Project.objects.filter(
            id=project.id,
            tenant_id=self.tenant_a,
        ).exists()

        assert Team.objects.filter(
            id=team.id,
            tenant_id=self.tenant_a,
        ).exists()

        assert Task.objects.filter(
            id=task.id,
            tenant_id=self.tenant_a,
            project_id=project.id,
        ).exists()

        assert Comment.objects.filter(
            id=comment.id,
            tenant_id=self.tenant_a,
            task_id=task.id,
        ).exists()

        assert Attachment.objects.filter(
            id=attachment.id,
            tenant_id=self.tenant_a,
            task_id=task.id,
        ).exists()

        assert Tag.objects.filter(
            id=tag.id,
            tenant_id=self.tenant_a,
        ).exists()

        assert TaskTag.objects.filter(
            id=task_tag.id,
            tenant_id=self.tenant_a,
            task_id=task.id,
            tag_id=tag.id,
        ).exists()

    def test_core_domains_are_isolated_between_tenants(self):
        """
        A resource created under Tenant A must not be accessible
        through Tenant B.
        """

        # Tenant A resources
        project = ProjectService.create_project(
            tenant_id=self.tenant_a,
            user_id=self.user_a,
            name="Tenant A Project",
        )

        task = TaskService.create_task(
            tenant_id=self.tenant_a,
            project_id=project.id,
            user_id=self.user_a,
            title="Tenant A Task",
        )

        comment = CommentService.create_comment(
            tenant_id=self.tenant_a,
            task_id=task.id,
            user_id=self.user_a,
            content={"text": "Tenant A comment"},
        )

        attachment = AttachmentService.create_attachment(
            tenant_id=self.tenant_a,
            task_id=task.id,
            user_id=self.user_a,
            s3_key="tenant-a/file.pdf",
            filename="file.pdf",
            content_type="application/pdf",
            size=100,
        )

        tag = TagService.create_tag(
            tenant_id=self.tenant_a,
            user_id=self.user_a,
            name="TenantA",
        )

        TagService.attach_tag_to_task(
            tenant_id=self.tenant_a,
            task_id=task.id,
            tag_id=tag.id,
        )

        # ---------------------------------------------------------
        # Project isolation
        # ---------------------------------------------------------

        with pytest.raises(ResourceNotFoundError):
            ProjectService.get_project(
                tenant_id=self.tenant_b,
                project_id=project.id,
            )

        # ---------------------------------------------------------
        # Task isolation
        # ---------------------------------------------------------

        with pytest.raises(ResourceNotFoundError):
            TaskService.get_task(
                tenant_id=self.tenant_b,
                task_id=task.id,
            )

        # ---------------------------------------------------------
        # Comment isolation
        # ---------------------------------------------------------

        with pytest.raises(ResourceNotFoundError):
            CommentService.get_comment(
                tenant_id=self.tenant_b,
                comment_id=comment.id,
            )

        # ---------------------------------------------------------
        # Attachment isolation
        # ---------------------------------------------------------

        with pytest.raises(ResourceNotFoundError):
            AttachmentService.get_attachment(
                tenant_id=self.tenant_b,
                attachment_id=attachment.id,
            )

        # ---------------------------------------------------------
        # Tag isolation
        # ---------------------------------------------------------

        with pytest.raises(ResourceNotFoundError):
            TagService.get_tag(
                tenant_id=self.tenant_b,
                tag_id=tag.id,
            )

    def test_cross_tenant_task_creation_is_rejected(self):
        project = ProjectService.create_project(
            tenant_id=self.tenant_a,
            user_id=self.user_a,
            name="Tenant A Project",
        )

        with pytest.raises(ResourceNotFoundError):
            TaskService.create_task(
                tenant_id=self.tenant_b,
                project_id=project.id,
                user_id=self.user_b,
                title="Unauthorized Task",
            )

        assert not Task.objects.filter(
            title="Unauthorized Task",
        ).exists()

    def test_cross_tenant_comment_creation_is_rejected(self):
        project = ProjectService.create_project(
            tenant_id=self.tenant_a,
            user_id=self.user_a,
            name="Tenant A Project",
        )

        task = TaskService.create_task(
            tenant_id=self.tenant_a,
            project_id=project.id,
            user_id=self.user_a,
            title="Tenant A Task",
        )

        with pytest.raises(ResourceNotFoundError):
            CommentService.create_comment(
                tenant_id=self.tenant_b,
                task_id=task.id,
                user_id=self.user_b,
                content={"text": "Unauthorized comment"},
            )

        assert not Comment.objects.filter(
            content={"text": "Unauthorized comment"},
        ).exists()

    def test_cross_tenant_attachment_creation_is_rejected(self):
        project = ProjectService.create_project(
            tenant_id=self.tenant_a,
            user_id=self.user_a,
            name="Tenant A Project",
        )

        task = TaskService.create_task(
            tenant_id=self.tenant_a,
            project_id=project.id,
            user_id=self.user_a,
            title="Tenant A Task",
        )

        with pytest.raises(ResourceNotFoundError):
            AttachmentService.create_attachment(
                tenant_id=self.tenant_b,
                task_id=task.id,
                user_id=self.user_b,
                s3_key="tenant-b/unauthorized.pdf",
                filename="unauthorized.pdf",
                content_type="application/pdf",
                size=100,
            )

        assert not Attachment.objects.filter(
            s3_key="tenant-b/unauthorized.pdf",
        ).exists()

    def test_cross_tenant_tag_assignment_is_rejected(self):
        project = ProjectService.create_project(
            tenant_id=self.tenant_a,
            user_id=self.user_a,
            name="Tenant A Project",
        )

        task = TaskService.create_task(
            tenant_id=self.tenant_a,
            project_id=project.id,
            user_id=self.user_a,
            title="Tenant A Task",
        )

        tag = TagService.create_tag(
            tenant_id=self.tenant_b,
            user_id=self.user_b,
            name="Tenant B Tag",
        )

        with pytest.raises(ResourceNotFoundError):
            TagService.attach_tag_to_task(
                tenant_id=self.tenant_a,
                task_id=task.id,
                tag_id=tag.id,
            )

        assert not TaskTag.objects.filter(
            task_id=task.id,
            tag_id=tag.id,
        ).exists()

    def test_listing_operations_remain_tenant_scoped(self):
        project_a = ProjectService.create_project(
            tenant_id=self.tenant_a,
            user_id=self.user_a,
            name="Tenant A Project",
        )

        project_b = ProjectService.create_project(
            tenant_id=self.tenant_b,
            user_id=self.user_b,
            name="Tenant B Project",
        )

        task_a = TaskService.create_task(
            tenant_id=self.tenant_a,
            project_id=project_a.id,
            user_id=self.user_a,
            title="Tenant A Task",
        )

        task_b = TaskService.create_task(
            tenant_id=self.tenant_b,
            project_id=project_b.id,
            user_id=self.user_b,
            title="Tenant B Task",
        )

        TeamService.create_team(
            tenant_id=self.tenant_a,
            user_id=self.user_a,
            name="Tenant A Team",
        )

        TeamService.create_team(
            tenant_id=self.tenant_b,
            user_id=self.user_b,
            name="Tenant B Team",
        )

        tenant_a_projects = ProjectService.list_projects(
            tenant_id=self.tenant_a,
        )

        tenant_a_tasks = TaskService.list_project_tasks(
            tenant_id=self.tenant_a,
            project_id=project_a.id,
        )

        tenant_a_teams = TeamService.list_teams(
            tenant_id=self.tenant_a,
        )

        assert {
            project.id for project in tenant_a_projects
        } == {project_a.id}

        assert {
            task.id for task in tenant_a_tasks
        } == {task_a.id}

        assert {
            team.tenant_id for team in tenant_a_teams
        } == {self.tenant_a}

        assert task_b.id not in {
            task.id for task in tenant_a_tasks
        }

        assert project_b.id not in {
            project.id for project in tenant_a_projects
        }

    def test_task_child_resources_follow_task_tenant_boundary(self):
        project = ProjectService.create_project(
            tenant_id=self.tenant_a,
            user_id=self.user_a,
            name="Tenant A Project",
        )

        task = TaskService.create_task(
            tenant_id=self.tenant_a,
            project_id=project.id,
            user_id=self.user_a,
            title="Tenant A Task",
        )

        comment = CommentService.create_comment(
            tenant_id=self.tenant_a,
            task_id=task.id,
            user_id=self.user_a,
            content={"text": "Comment"},
        )

        attachment = AttachmentService.create_attachment(
            tenant_id=self.tenant_a,
            task_id=task.id,
            user_id=self.user_a,
            s3_key="tenant-a/task-file.pdf",
            filename="task-file.pdf",
            content_type="application/pdf",
            size=200,
        )

        tag = TagService.create_tag(
            tenant_id=self.tenant_a,
            user_id=self.user_a,
            name="TaskTag",
        )

        TagService.attach_tag_to_task(
            tenant_id=self.tenant_a,
            task_id=task.id,
            tag_id=tag.id,
        )

        comments = CommentService.list_task_comments(
            tenant_id=self.tenant_a,
            task_id=task.id,
        )

        attachments = AttachmentService.list_task_attachments(
            tenant_id=self.tenant_a,
            task_id=task.id,
        )

        tags = TagService.list_task_tags(
            tenant_id=self.tenant_a,
            task_id=task.id,
        )

        assert {item.id for item in comments} == {comment.id}
        assert {item.id for item in attachments} == {attachment.id}
        assert {item.id for item in tags} == {tag.id}

        with pytest.raises(ResourceNotFoundError):
            CommentService.list_task_comments(
                tenant_id=self.tenant_b,
                task_id=task.id,
            )

        with pytest.raises(ResourceNotFoundError):
            AttachmentService.list_task_attachments(
                tenant_id=self.tenant_b,
                task_id=task.id,
            )

        # Tag listing currently queries by tenant_id + task_id.
        assert list(
            TagService.list_task_tags(
                tenant_id=self.tenant_b,
                task_id=task.id,
            )
        ) == []