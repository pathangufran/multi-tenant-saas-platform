import pytest
from types import SimpleNamespace
from unittest.mock import patch
from rest_framework.test import APIRequestFactory
from apps.comments.views import (
    TaskCommentCreateView,
    TaskCommentDeleteView,
    TaskCommentListView,
    TaskCommentUpdateView,
)
from apps.projects.views import (
    ProjectCreateView,
    ProjectDeleteView,
    ProjectDetailView,
    ProjectListView,
    ProjectUpdateView,
)
from apps.tasks.views import (
    ProjectTaskCreateView,
    ProjectTaskDeleteView,
    ProjectTaskDetailsView,
    ProjectTaskListView,
    ProjectTaskUpdateView,
)
from apps.teams.views import (
    TeamCreateView,
    TeamDeleteView,
    TeamDetailView,
    TeamListView,
    TeamUpdateView,
)
from apps.attachments.views import (
    TaskAttachmentCreateView,
    TaskAttachmentDeleteView,
    TaskAttachmentDetailView,
    TaskAttachmentListView,
)
from apps.tags.views import (
    TagCreateView,
    TagDeleteView,
    TagDetailView,
    TagListView,
    TagUpdateView,
    TaskTagCreateView,
    TaskTagDeleteView,
    TaskTagListView,
)

@pytest.mark.django_db
class TestCoreAPIRBACPermissions:
    def setup_method(self):
        self.factory = APIRequestFactory()

    def _request(self, method):
        request_method = getattr(self.factory, method.lower())

        request = request_method(
            "/api/v1/test/",
        )

        request.user = SimpleNamespace(
            is_authenticated=True,
        )

        return request

    def _assert_permission(
        self,
        view_class,
        method,
        expected_permission,
    ):
        request = self._request(method)

        view = view_class()

        request.method = method.upper()
        view.request = request

        with patch(
            "apps.common.rbac."
            "TenantServiceRBACPermission.has_permission",
            return_value=True,
        ):
            permissions = view.get_permissions()

        rbac_permission = next(
            permission
            for permission in permissions
            if permission.__class__.__name__
            == "TenantServiceRBACPermission"
        )

        assert view.required_permission == expected_permission
        assert rbac_permission is not None

    # ------------------------------------------------------------------
    # Project permissions
    # ------------------------------------------------------------------

    def test_project_create_requires_projects_create(self):
        self._assert_permission(
            ProjectCreateView,
            "POST",
            "projects.create",
        )

    def test_project_list_requires_projects_read(self):
        self._assert_permission(
            ProjectListView,
            "GET",
            "projects.read",
        )

    def test_project_detail_get_requires_projects_read(self):
        self._assert_permission(
            ProjectDetailView,
            "GET",
            "projects.read",
        )

    def test_project_detail_patch_requires_projects_update(self):
        self._assert_permission(
            ProjectDetailView,
            "PATCH",
            "projects.update",
        )

    def test_project_detail_delete_requires_projects_delete(self):
        self._assert_permission(
            ProjectDetailView,
            "DELETE",
            "projects.delete",
        )

    def test_project_update_requires_projects_update(self):
        self._assert_permission(
            ProjectUpdateView,
            "PATCH",
            "projects.update",
        )

    def test_project_delete_requires_projects_delete(self):
        self._assert_permission(
            ProjectDeleteView,
            "DELETE",
            "projects.delete",
        )

    # ------------------------------------------------------------------
    # Team permissions
    # ------------------------------------------------------------------

    def test_team_create_requires_teams_create(self):
        self._assert_permission(
            TeamCreateView,
            "POST",
            "teams.create",
        )

    def test_team_list_requires_teams_read(self):
        self._assert_permission(
            TeamListView,
            "GET",
            "teams.read",
        )

    def test_team_detail_get_requires_teams_read(self):
        self._assert_permission(
            TeamDetailView,
            "GET",
            "teams.read",
        )

    def test_team_detail_patch_requires_teams_update(self):
        self._assert_permission(
            TeamDetailView,
            "PATCH",
            "teams.update",
        )

    def test_team_detail_delete_requires_teams_delete(self):
        self._assert_permission(
            TeamDetailView,
            "DELETE",
            "teams.delete",
        )

    def test_team_update_requires_teams_update(self):
        self._assert_permission(
            TeamUpdateView,
            "PATCH",
            "teams.update",
        )

    def test_team_delete_requires_teams_delete(self):
        self._assert_permission(
            TeamDeleteView,
            "DELETE",
            "teams.delete",
        )

    # ------------------------------------------------------------------
    # Task permissions
    # ------------------------------------------------------------------

    def test_task_create_requires_tasks_create(self):
        self._assert_permission(
            ProjectTaskCreateView,
            "POST",
            "tasks.create",
        )

    def test_task_list_requires_tasks_read(self):
        self._assert_permission(
            ProjectTaskListView,
            "GET",
            "tasks.read",
        )

    def test_task_detail_get_requires_tasks_read(self):
        self._assert_permission(
            ProjectTaskDetailsView,
            "GET",
            "tasks.read",
        )

    def test_task_detail_patch_requires_tasks_update(self):
        self._assert_permission(
            ProjectTaskDetailsView,
            "PATCH",
            "tasks.update",
        )

    def test_task_detail_delete_requires_tasks_delete(self):
        self._assert_permission(
            ProjectTaskDetailsView,
            "DELETE",
            "tasks.delete",
        )

    def test_task_update_requires_tasks_update(self):
        self._assert_permission(
            ProjectTaskUpdateView,
            "PATCH",
            "tasks.update",
        )

    def test_task_delete_requires_tasks_delete(self):
        self._assert_permission(
            ProjectTaskDeleteView,
            "DELETE",
            "tasks.delete",
        )

    # ------------------------------------------------------------------
    # Comment permissions
    # ------------------------------------------------------------------

    def test_comment_create_requires_comments_create(self):
        self._assert_permission(
            TaskCommentCreateView,
            "POST",
            "comments.create",
        )

    def test_comment_list_requires_comments_read(self):
        self._assert_permission(
            TaskCommentListView,
            "GET",
            "comments.read",
        )

    def test_comment_detail_get_requires_comments_read(self):
        self._assert_permission(
            TaskCommentDetailView,
            "GET",
            "comments.read",
        )

    def test_comment_detail_patch_requires_comments_update(self):
        self._assert_permission(
            TaskCommentDetailView,
            "PATCH",
            "comments.update",
        )

    def test_comment_detail_delete_requires_comments_delete(self):
        self._assert_permission(
            TaskCommentDetailView,
            "DELETE",
            "comments.delete",
        )

    def test_comment_update_requires_comments_update(self):
        self._assert_permission(
            TaskCommentUpdateView,
            "PATCH",
            "comments.update",
        )

    def test_comment_delete_requires_comments_delete(self):
        self._assert_permission(
            TaskCommentDeleteView,
            "DELETE",
            "comments.delete",
        )

    # ------------------------------------------------------------------
    # Attachment permissions
    # ------------------------------------------------------------------

    def test_attachment_create_requires_attachments_create(self):
        self._assert_permission(
            TaskAttachmentCreateView,
            "POST",
            "attachments.create",
        )

    def test_attachment_list_requires_attachments_read(self):
        self._assert_permission(
            TaskAttachmentListView,
            "GET",
            "attachments.read",
        )

    def test_attachment_detail_requires_attachments_read(self):
        self._assert_permission(
            TaskAttachmentDetailView,
            "GET",
            "attachments.read",
        )

    def test_attachment_delete_requires_attachments_delete(self):
        self._assert_permission(
            TaskAttachmentDeleteView,
            "DELETE",
            "attachments.delete",
        )

    # ------------------------------------------------------------------
    # Tag permissions
    # ------------------------------------------------------------------

    def test_tag_create_requires_tags_create(self):
        self._assert_permission(
            TagCreateView,
            "POST",
            "tags.create",
        )

    def test_tag_list_requires_tags_read(self):
        self._assert_permission(
            TagListView,
            "GET",
            "tags.read",
        )

    def test_tag_detail_requires_tags_read(self):
        self._assert_permission(
            TagDetailView,
            "GET",
            "tags.read",
        )

    def test_tag_update_requires_tags_update(self):
        self._assert_permission(
            TagUpdateView,
            "PATCH",
            "tags.update",
        )

    def test_tag_delete_requires_tags_delete(self):
        self._assert_permission(
            TagDeleteView,
            "DELETE",
            "tags.delete",
        )

    def test_task_tag_create_requires_tags_assign(self):
        self._assert_permission(
            TaskTagCreateView,
            "POST",
            "tags.assign",
        )

    def test_task_tag_list_requires_tags_read(self):
        self._assert_permission(
            TaskTagListView,
            "GET",
            "tags.read",
        )

    def test_task_tag_delete_requires_tags_assign(self):
        self._assert_permission(
            TaskTagDeleteView,
            "DELETE",
            "tags.assign",
        )