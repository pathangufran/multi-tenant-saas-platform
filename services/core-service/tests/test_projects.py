import uuid
import pytest
from rest_framework.test import APIRequestFactory
from apps.projects.models import Project
from apps.projects.services import ProjectService


@pytest.mark.django_db
class TestProjectService:

    def setup_method(self):
        self.tenant_id = uuid.uuid4()
        self.other_tenant_id = uuid.uuid4()
        self.user_id = uuid.uuid4()

    def test_create_project(self):
        project = ProjectService.create_project(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Website Redesign",
            description="Redesign company website",
        )

        assert project.id is not None
        assert project.tenant_id == self.tenant_id
        assert project.name == "Website Redesign"
        assert project.description == "Redesign company website"
        assert project.created_by == self.user_id
        assert project.status == Project.Status.ACTIVE

    def test_create_project_defaults_to_active(self):
        project = ProjectService.create_project(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Backend Migration",
        )

        assert project.status == Project.Status.ACTIVE

    def test_update_project(self):
        project = ProjectService.create_project(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Old Name",
        )

        updated_project = ProjectService.update_project(
            tenant_id=self.tenant_id,
            project_id=project.id,
            data={
                "name": "New Name",
                "description": "Updated description",
            },
        )

        assert updated_project.name == "New Name"
        assert updated_project.description == "Updated description"

    def test_delete_project(self):
        project = ProjectService.create_project(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Temporary Project",
        )

        ProjectService.delete_project(
            tenant_id=self.tenant_id,
            project_id=project.id,
        )

        assert not Project.objects.filter(
            id=project.id,
        ).exists()

    def test_get_project_for_tenant(self):
        project = ProjectService.create_project(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Tenant Project",
        )

        result = ProjectService.get_project(
            tenant_id=self.tenant_id,
            project_id=project.id,
        )

        assert result.id == project.id

    def test_cross_tenant_project_is_not_visible(self):
        project = ProjectService.create_project(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Private Project",
        )

        with pytest.raises(Exception):
            ProjectService.get_project(
                tenant_id=self.other_tenant_id,
                project_id=project.id,
            )

    def test_list_projects_only_returns_current_tenant(self):
        own_project = ProjectService.create_project(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Own Project",
        )

        ProjectService.create_project(
            tenant_id=self.other_tenant_id,
            user_id=self.user_id,
            name="Other Tenant Project",
        )

        projects = ProjectService.list_projects(
            tenant_id=self.tenant_id,
        )

        project_ids = {project.id for project in projects}

        assert own_project.id in project_ids
        assert len(project_ids) == 1

    def test_active_projects_only(self):
        active_project = ProjectService.create_project(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Active Project",
        )

        archived_project = ProjectService.create_project(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Archived Project",
        )

        ProjectService.update_project(
            tenant_id=self.tenant_id,
            project_id=archived_project.id,
            data={
                "status": Project.Status.ARCHIVED,
            },
        )

        projects = ProjectService.get_active_projects(
            tenant_id=self.tenant_id,
        )

        project_ids = {project.id for project in projects}

        assert active_project.id in project_ids
        assert archived_project.id not in project_ids

@pytest.mark.django_db
class TestProjectIsolation:

    def setup_method(self):
        self.tenant_a = uuid.uuid4()
        self.tenant_b = uuid.uuid4()
        self.user_id = uuid.uuid4()

    def test_tenant_a_cannot_update_tenant_b_project(self):
        project = ProjectService.create_project(
            tenant_id=self.tenant_a,
            user_id=self.user_id,
            name="Tenant A Project",
        )

        with pytest.raises(Exception):
            ProjectService.update_project(
                tenant_id=self.tenant_b,
                project_id=project.id,
                data={
                    "name": "Hacked Project",
                },
            )

        project.refresh_from_db()

        assert project.name == "Tenant A Project"

    def test_tenant_a_cannot_delete_tenant_b_project(self):
        project = ProjectService.create_project(
            tenant_id=self.tenant_a,
            user_id=self.user_id,
            name="Tenant A Project",
        )

        with pytest.raises(Exception):
            ProjectService.delete_project(
                tenant_id=self.tenant_b,
                project_id=project.id,
            )

        assert Project.objects.filter(
            id=project.id,
        ).exists()