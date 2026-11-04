import uuid
import pytest
from apps.comments.models import Comment
from apps.comments.services import CommentService
from apps.common.exceptions import ResourceNotFoundError
from apps.tasks.models import Task

@pytest.mark.django_db
class TestCommentService:

    def test_create_comment(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_id,
            project_id=uuid.uuid4(),
            title="Test task",
            description="Test description",
            created_by=user_id,
        )

        comment = CommentService.create_comment(
            tenant_id=tenant_id,
            task_id=task.id,
            user_id=user_id,
            content="This is a test comment.",
        )

        assert comment.id is not None
        assert comment.tenant_id == tenant_id
        assert comment.task_id == task.id
        assert comment.created_by == user_id
        assert comment.content == "This is a test comment."

    def test_create_comment_for_non_existing_task(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        with pytest.raises(ResourceNotFoundError):
            CommentService.create_comment(
                tenant_id=tenant_id,
                task_id=uuid.uuid4(),
                user_id=user_id,
                content="Test comment",
            )

    def test_create_comment_for_other_tenant_task(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_b,
            project_id=uuid.uuid4(),
            title="Tenant B Task",
            created_by=user_id,
        )

        with pytest.raises(ResourceNotFoundError):
            CommentService.create_comment(
                tenant_id=tenant_a,
                task_id=task.id,
                user_id=user_id,
                content="Cross tenant comment",
            )

    def test_update_comment(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_id,
            project_id=uuid.uuid4(),
            title="Test task",
            created_by=user_id,
        )

        comment = Comment.objects.create(
            tenant_id=tenant_id,
            task_id=task.id,
            content="Original comment",
            created_by=user_id,
        )

        updated_comment = CommentService.update_comment(
            tenant_id=tenant_id,
            comment_id=comment.id,
            content="Updated comment",
        )

        updated_comment.refresh_from_db()

        assert updated_comment.content == "Updated comment"

    def test_update_cross_tenant_comment_fails(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_b,
            project_id=uuid.uuid4(),
            title="Tenant B Task",
            created_by=user_id,
        )

        comment = Comment.objects.create(
            tenant_id=tenant_b,
            task_id=task.id,
            content="Tenant B comment",
            created_by=user_id,
        )

        with pytest.raises(ResourceNotFoundError):
            CommentService.update_comment(
                tenant_id=tenant_a,
                comment_id=comment.id,
                content="Unauthorized update",
            )

    def test_delete_comment(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_id,
            project_id=uuid.uuid4(),
            title="Test task",
            created_by=user_id,
        )

        comment = Comment.objects.create(
            tenant_id=tenant_id,
            task_id=task.id,
            content="Delete me",
            created_by=user_id,
        )

        CommentService.delete_comment(
            tenant_id=tenant_id,
            comment_id=comment.id,
        )

        assert not Comment.objects.filter(
            id=comment.id
        ).exists()

    def test_delete_cross_tenant_comment_fails(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_b,
            project_id=uuid.uuid4(),
            title="Tenant B Task",
            created_by=user_id,
        )

        comment = Comment.objects.create(
            tenant_id=tenant_b,
            task_id=task.id,
            content="Tenant B comment",
            created_by=user_id,
        )

        with pytest.raises(ResourceNotFoundError):
            CommentService.delete_comment(
                tenant_id=tenant_a,
                comment_id=comment.id,
            )

    def test_get_comment(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_id,
            project_id=uuid.uuid4(),
            title="Test task",
            created_by=user_id,
        )

        comment = Comment.objects.create(
            tenant_id=tenant_id,
            task_id=task.id,
            content="Test comment",
            created_by=user_id,
        )

        result = CommentService.get_comment(
            tenant_id=tenant_id,
            comment_id=comment.id,
        )

        assert result.id == comment.id

    def test_get_comment_cross_tenant_is_hidden(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_b,
            project_id=uuid.uuid4(),
            title="Tenant B Task",
            created_by=user_id,
        )

        comment = Comment.objects.create(
            tenant_id=tenant_b,
            task_id=task.id,
            content="Tenant B comment",
            created_by=user_id,
        )

        with pytest.raises(ResourceNotFoundError):
            CommentService.get_comment(
                tenant_id=tenant_a,
                comment_id=comment.id,
            )

    def test_list_task_comments(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_id,
            project_id=uuid.uuid4(),
            title="Test task",
            created_by=user_id,
        )

        first = Comment.objects.create(
            tenant_id=tenant_id,
            task_id=task.id,
            content="First",
            created_by=user_id,
        )

        second = Comment.objects.create(
            tenant_id=tenant_id,
            task_id=task.id,
            content="Second",
            created_by=user_id,
        )

        comments = list(CommentService.list_task_comments(
            tenant_id=tenant_id,
            task_id=task.id,
        ))

        assert len(comments) == 2
        assert {comment.id for comment in comments} == {
            first.id,
            second.id,
        }

    def test_list_task_comments_does_not_return_other_tenant(self):
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

        Comment.objects.create(
            tenant_id=tenant_a,
            task_id=task_a.id,
            content="Tenant A comment",
            created_by=uuid.uuid4(),
        )

        Comment.objects.create(
            tenant_id=tenant_b,
            task_id=task_b.id,
            content="Tenant B comment",
            created_by=uuid.uuid4(),
        )

        comments = CommentService.list_task_comments(
            tenant_id=tenant_a,
            task_id=task_b.id,
        )

        assert comments.count() == 0

    def test_list_user_comments(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_id,
            project_id=uuid.uuid4(),
            title="Test task",
            created_by=user_id,
        )

        Comment.objects.create(
            tenant_id=tenant_id,
            task_id=task.id,
            content="First",
            created_by=user_id,
        )

        Comment.objects.create(
            tenant_id=tenant_id,
            task_id=task.id,
            content="Second",
            created_by=user_id,
        )

        comments = CommentService.list_user_comments(
            tenant_id=tenant_id,
            user_id=user_id,
        )

        assert comments.count() == 2

@pytest.mark.django_db
class TestCommentModel:

    def test_comment_requires_tenant(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        comment = Comment.objects.create(
            tenant_id=tenant_id,
            task_id=uuid.uuid4(),
            content="Tenant scoped comment",
            created_by=user_id,
        )

        assert comment.tenant_id == tenant_id

    def test_comments_can_have_same_content(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        task = Task.objects.create(
            tenant_id=tenant_id,
            project_id=uuid.uuid4(),
            title="Test task",
            created_by=user_id,
        )

        Comment.objects.create(
            tenant_id=tenant_id,
            task_id=task.id,
            content="Same content",
            created_by=user_id,
        )

        Comment.objects.create(
            tenant_id=tenant_id,
            task_id=task.id,
            content="Same content",
            created_by=user_id,
        )

        assert Comment.objects.filter(
            tenant_id=tenant_id,
            task_id=task.id,
        ).count() == 2