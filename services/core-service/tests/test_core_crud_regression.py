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
class TestProjectCRUDRegression:

    def setup_method(self):
        self.tenant_id = uuid.uuid4()
        self.other_tenant_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

    def test_project_full_lifecycle(self):
        project = ProjectService.create_project(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Initial Project",
            description="Initial description",
        )

        assert Project.objects.filter(
            id=project.id,
            tenant_id=self.tenant_id,
        ).exists()

        fetched = ProjectService.get_project(
            tenant_id=self.tenant_id,
            project_id=project.id,
        )

        assert fetched.id == project.id

        updated = ProjectService.update_project(
            tenant_id=self.tenant_id,
            project_id=project.id,
            data={
                "name": "Updated Project",
                "description": "Updated description",
            },
        )

        assert updated.name == "Updated Project"
        assert updated.description == "Updated description"

        ProjectService.delete_project(
            tenant_id=self.tenant_id,
            project_id=project.id,
        )

        assert not Project.objects.filter(
            id=project.id,
        ).exists()

    def test_project_cross_tenant_access_is_rejected(self):
        project = ProjectService.create_project(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Private Project",
        )

        with pytest.raises(ResourceNotFoundError):
            ProjectService.get_project(
                tenant_id=self.other_tenant_id,
                project_id=project.id,
            )

        with pytest.raises(ResourceNotFoundError):
            ProjectService.update_project(
                tenant_id=self.other_tenant_id,
                project_id=project.id,
                data={"name": "Hacked"},
            )

        with pytest.raises(ResourceNotFoundError):
            ProjectService.delete_project(
                tenant_id=self.other_tenant_id,
                project_id=project.id,
            )

        project.refresh_from_db()

        assert project.name == "Private Project"


@pytest.mark.django_db
class TestTeamCRUDRegression:

    def setup_method(self):
        self.tenant_id = uuid.uuid4()
        self.other_tenant_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

    def test_team_full_lifecycle(self):
        team = TeamService.create_team(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Engineering",
            description="Engineering team",
        )

        fetched = TeamService.get_team(
            tenant_id=self.tenant_id,
            team_id=team.id,
        )

        assert fetched.id == team.id

        updated = TeamService.update_team(
            tenant_id=self.tenant_id,
            team_id=team.id,
            data={
                "name": "Platform Engineering",
                "description": "Platform team",
            },
        )

        assert updated.name == "Platform Engineering"
        assert updated.description == "Platform team"

        TeamService.delete_team(
            tenant_id=self.tenant_id,
            team_id=team.id,
        )

        assert not Team.objects.filter(
            id=team.id,
        ).exists()

    def test_team_cross_tenant_access_is_rejected(self):
        team = TeamService.create_team(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Private Team",
        )

        with pytest.raises(ResourceNotFoundError):
            TeamService.get_team(
                tenant_id=self.other_tenant_id,
                team_id=team.id,
            )

        with pytest.raises(ResourceNotFoundError):
            TeamService.update_team(
                tenant_id=self.other_tenant_id,
                team_id=team.id,
                data={"name": "Hacked Team"},
            )

        with pytest.raises(ResourceNotFoundError):
            TeamService.delete_team(
                tenant_id=self.other_tenant_id,
                team_id=team.id,
            )

        team.refresh_from_db()

        assert team.name == "Private Team"


@pytest.mark.django_db
class TestTaskCRUDRegression:

    def setup_method(self):
        self.tenant_id = uuid.uuid4()
        self.other_tenant_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

        self.project = Project.objects.create(
            tenant_id=self.tenant_id,
            name="Task Project",
            created_by=self.user_id,
        )

    def test_task_full_lifecycle(self):
        task = TaskService.create_task(
            tenant_id=self.tenant_id,
            project_id=self.project.id,
            user_id=self.user_id,
            title="Initial Task",
            description="Initial description",
            priority=Task.Priority.MEDIUM,
        )

        fetched = TaskService.get_task(
            tenant_id=self.tenant_id,
            task_id=task.id,
        )

        assert fetched.id == task.id

        updated = TaskService.update_task(
            tenant_id=self.tenant_id,
            task_id=task.id,
            data={
                "title": "Updated Task",
                "description": "Updated description",
                "priority": Task.Priority.HIGH,
                "status": Task.Status.IN_PROGRESS,
            },
        )

        assert updated.title == "Updated Task"
        assert updated.description == "Updated description"
        assert updated.priority == Task.Priority.HIGH
        assert updated.status == Task.Status.IN_PROGRESS

        TaskService.delete_task(
            tenant_id=self.tenant_id,
            task_id=task.id,
        )

        assert not Task.objects.filter(
            id=task.id,
        ).exists()

    def test_task_cross_tenant_access_is_rejected(self):
        task = TaskService.create_task(
            tenant_id=self.tenant_id,
            project_id=self.project.id,
            user_id=self.user_id,
            title="Private Task",
        )

        with pytest.raises(ResourceNotFoundError):
            TaskService.get_task(
                tenant_id=self.other_tenant_id,
                task_id=task.id,
            )

        with pytest.raises(ResourceNotFoundError):
            TaskService.update_task(
                tenant_id=self.other_tenant_id,
                task_id=task.id,
                data={"title": "Hacked Task"},
            )

        with pytest.raises(ResourceNotFoundError):
            TaskService.delete_task(
                tenant_id=self.other_tenant_id,
                task_id=task.id,
            )

        task.refresh_from_db()

        assert task.title == "Private Task"

    def test_task_cannot_be_created_under_foreign_project(self):
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


@pytest.mark.django_db
class TestCommentCRUDRegression:

    def setup_method(self):
        self.tenant_id = uuid.uuid4()
        self.other_tenant_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

        self.project = Project.objects.create(
            tenant_id=self.tenant_id,
            name="Comment Project",
            created_by=self.user_id,
        )

        self.task = Task.objects.create(
            tenant_id=self.tenant_id,
            project_id=self.project.id,
            title="Comment Task",
            created_by=self.user_id,
        )

    def test_comment_full_lifecycle(self):
        comment = CommentService.create_comment(
            tenant_id=self.tenant_id,
            task_id=self.task.id,
            user_id=self.user_id,
            content={"text": "Initial comment"},
        )

        fetched = CommentService.get_comment(
            tenant_id=self.tenant_id,
            comment_id=comment.id,
        )

        assert fetched.id == comment.id

        updated = CommentService.update_comment(
            tenant_id=self.tenant_id,
            comment_id=comment.id,
            content={"text": "Updated comment"},
        )

        assert updated.content == {"text": "Updated comment"}

        CommentService.delete_comment(
            tenant_id=self.tenant_id,
            comment_id=comment.id,
        )

        assert not Comment.objects.filter(
            id=comment.id,
        ).exists()

    def test_comment_cross_tenant_access_is_rejected(self):
        comment = CommentService.create_comment(
            tenant_id=self.tenant_id,
            task_id=self.task.id,
            user_id=self.user_id,
            content={"text": "Private comment"},
        )

        with pytest.raises(ResourceNotFoundError):
            CommentService.get_comment(
                tenant_id=self.other_tenant_id,
                comment_id=comment.id,
            )

        with pytest.raises(ResourceNotFoundError):
            CommentService.update_comment(
                tenant_id=self.other_tenant_id,
                comment_id=comment.id,
                content={"text": "Hacked comment"},
            )

        with pytest.raises(ResourceNotFoundError):
            CommentService.delete_comment(
                tenant_id=self.other_tenant_id,
                comment_id=comment.id,
            )

        comment.refresh_from_db()

        assert comment.content == {"text": "Private comment"}

    def test_comment_cannot_be_created_under_foreign_task(self):
        with pytest.raises(ResourceNotFoundError):
            CommentService.create_comment(
                tenant_id=self.other_tenant_id,
                task_id=self.task.id,
                user_id=self.user_id,
                content={"text": "Unauthorized"},
            )

        assert not Comment.objects.filter(
            content={"text": "Unauthorized"},
        ).exists()


@pytest.mark.django_db
class TestAttachmentCRUDRegression:

    def setup_method(self):
        self.tenant_id = uuid.uuid4()
        self.other_tenant_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

        self.project = Project.objects.create(
            tenant_id=self.tenant_id,
            name="Attachment Project",
            created_by=self.user_id,
        )

        self.task = Task.objects.create(
            tenant_id=self.tenant_id,
            project_id=self.project.id,
            title="Attachment Task",
            created_by=self.user_id,
        )

    def test_attachment_create_read_delete_lifecycle(self):
        attachment = AttachmentService.create_attachment(
            tenant_id=self.tenant_id,
            task_id=self.task.id,
            user_id=self.user_id,
            s3_key="tenant-a/file.pdf",
            filename="file.pdf",
            content_type="application/pdf",
            size=1024,
        )

        fetched = AttachmentService.get_attachment(
            tenant_id=self.tenant_id,
            attachment_id=attachment.id,
        )

        assert fetched.id == attachment.id
        assert fetched.filename == "file.pdf"

        AttachmentService.delete_attachment(
            tenant_id=self.tenant_id,
            attachment_id=attachment.id,
        )

        assert not Attachment.objects.filter(
            id=attachment.id,
        ).exists()

    def test_attachment_cross_tenant_access_is_rejected(self):
        attachment = AttachmentService.create_attachment(
            tenant_id=self.tenant_id,
            task_id=self.task.id,
            user_id=self.user_id,
            s3_key="tenant-a/private.pdf",
            filename="private.pdf",
            content_type="application/pdf",
            size=100,
        )

        with pytest.raises(ResourceNotFoundError):
            AttachmentService.get_attachment(
                tenant_id=self.other_tenant_id,
                attachment_id=attachment.id,
            )

        with pytest.raises(ResourceNotFoundError):
            AttachmentService.delete_attachment(
                tenant_id=self.other_tenant_id,
                attachment_id=attachment.id,
            )

        assert Attachment.objects.filter(
            id=attachment.id,
        ).exists()

    def test_attachment_cannot_be_created_under_foreign_task(self):
        with pytest.raises(ResourceNotFoundError):
            AttachmentService.create_attachment(
                tenant_id=self.other_tenant_id,
                task_id=self.task.id,
                user_id=self.user_id,
                s3_key="tenant-b/unauthorized.pdf",
                filename="unauthorized.pdf",
                content_type="application/pdf",
                size=100,
            )

        assert not Attachment.objects.filter(
            s3_key="tenant-b/unauthorized.pdf",
        ).exists()


@pytest.mark.django_db
class TestTagCRUDRegression:

    def setup_method(self):
        self.tenant_id = uuid.uuid4()
        self.other_tenant_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

        self.project = Project.objects.create(
            tenant_id=self.tenant_id,
            name="Tag Project",
            created_by=self.user_id,
        )

        self.task = Task.objects.create(
            tenant_id=self.tenant_id,
            project_id=self.project.id,
            title="Tag Task",
            created_by=self.user_id,
        )

    def test_tag_full_lifecycle(self):
        tag = TagService.create_tag(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Backend",
        )

        fetched = TagService.get_tag(
            tenant_id=self.tenant_id,
            tag_id=tag.id,
        )

        assert fetched.id == tag.id

        updated = TagService.update_tag(
            tenant_id=self.tenant_id,
            tag_id=tag.id,
            name="Python Backend",
        )

        assert updated.name == "Python Backend"

        task_tag = TagService.attach_tag_to_task(
            tenant_id=self.tenant_id,
            task_id=self.task.id,
            tag_id=tag.id,
        )

        assert task_tag.task_id == self.task.id
        assert task_tag.tag_id == tag.id

        tags = TagService.list_task_tags(
            tenant_id=self.tenant_id,
            task_id=self.task.id,
        )

        assert {
            item.id for item in tags
        } == {tag.id}

        TagService.remove_tag_from_task(
            tenant_id=self.tenant_id,
            task_id=self.task.id,
            tag_id=tag.id,
        )

        assert not TaskTag.objects.filter(
            task_id=self.task.id,
            tag_id=tag.id,
        ).exists()

        TagService.delete_tag(
            tenant_id=self.tenant_id,
            tag_id=tag.id,
        )

        assert not Tag.objects.filter(
            id=tag.id,
        ).exists()

    def test_tag_cross_tenant_access_is_rejected(self):
        tag = TagService.create_tag(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Private",
        )

        with pytest.raises(ResourceNotFoundError):
            TagService.get_tag(
                tenant_id=self.other_tenant_id,
                tag_id=tag.id,
            )

        with pytest.raises(ResourceNotFoundError):
            TagService.update_tag(
                tenant_id=self.other_tenant_id,
                tag_id=tag.id,
                name="Hacked",
            )

        with pytest.raises(ResourceNotFoundError):
            TagService.delete_tag(
                tenant_id=self.other_tenant_id,
                tag_id=tag.id,
            )

        tag.refresh_from_db()

        assert tag.name == "Private"

    def test_tag_assignment_cross_tenant_is_rejected(self):
        foreign_tag = TagService.create_tag(
            tenant_id=self.other_tenant_id,
            user_id=self.user_id,
            name="Foreign Tag",
        )

        with pytest.raises(ResourceNotFoundError):
            TagService.attach_tag_to_task(
                tenant_id=self.tenant_id,
                task_id=self.task.id,
                tag_id=foreign_tag.id,
            )

        assert not TaskTag.objects.filter(
            task_id=self.task.id,
            tag_id=foreign_tag.id,
        ).exists()