import uuid
import pytest
from apps.common.exceptions import (
    ConflictError,
    ResourceNotFoundError,
)
from apps.teams.models import Team
from apps.teams.services import TeamService

@pytest.mark.django_db
class TestTeamService:

    def setup_method(self):
        self.tenant_a = uuid.uuid4()
        self.tenant_id = uuid.uuid4()
        self.tenant_b = uuid.uuid4()
        self.user_id = uuid.uuid4()

    def test_create_team(self):
        team = TeamService.create_team(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Engineering",
            description="Engineering team",
        )

        assert team.id is not None
        assert team.tenant_id == self.tenant_id
        assert team.name == "Engineering"
        assert team.description == "Engineering team"
        assert team.created_by == self.user_id

    def test_create_team_without_description(self):
        team = TeamService.create_team(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Engineering",
        )

        assert team.description == ""

    def test_duplicate_team_name_same_tenant_fails(self):
        TeamService.create_team(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Engineering",
        )

        with pytest.raises(ConflictError):
            TeamService.create_team(
                tenant_id=self.tenant_id,
                user_id=self.user_id,
                name="Engineering",
            )

    def test_same_team_name_allowed_for_different_tenants(self):
        tenant_a = uuid.uuid4()
        tenant_b = uuid.uuid4()

        team_a = TeamService.create_team(
            tenant_id=tenant_a,
            user_id=self.user_id,
            name="Engineering",
        )

        team_b = TeamService.create_team(
            tenant_id=tenant_b,
            user_id=self.user_id,
            name="Engineering",
        )

        assert team_a.name == team_b.name
        assert team_a.tenant_id != team_b.tenant_id

    def test_update_team(self):
        team = TeamService.create_team(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Engineering",
        )

        updated_team = TeamService.update_team(
            tenant_id=self.tenant_id,
            team_id=team.id,
            data={
                "name": "Platform Engineering",
                "description": "Platform team",
            },
        )

        assert updated_team.name == "Platform Engineering"
        assert updated_team.description == "Platform team"

    def test_update_team_to_duplicate_name_fails(self):
        TeamService.create_team(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Engineering",
        )

        second_team = TeamService.create_team(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Platform",
        )

        with pytest.raises(ConflictError):
            TeamService.update_team(
                tenant_id=self.tenant_id,
                team_id=second_team.id,
                data={
                    "name": "Engineering",
                },
            )

    def test_delete_team(self):
        team = TeamService.create_team(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            name="Engineering",
        )

        TeamService.delete_team(
            tenant_id=self.tenant_id,
            team_id=team.id,
        )

        assert not Team.objects.filter(
            id=team.id,
        ).exists()

    def test_get_team(self):
        team = TeamService.create_team(
            tenant_id=self.tenant_a,
            user_id=self.user_id,
            name="Engineering",
        )

        result = TeamService.get_team(
            tenant_id=self.tenant_a,
            team_id=team.id,
        )

        assert result.id == team.id

    def test_cross_tenant_team_is_not_visible(self):
        team = TeamService.create_team(
            tenant_id=self.tenant_a,
            user_id=self.user_id,
            name="Engineering",
        )

        with pytest.raises(ResourceNotFoundError):
            TeamService.get_team(
                tenant_id=self.tenant_b,
                team_id=team.id,
            )

    def test_list_teams_is_tenant_scoped(self):
        own_team = TeamService.create_team(
            tenant_id=self.tenant_a,
            user_id=self.user_id,
            name="Engineering",
        )

        TeamService.create_team(
            tenant_id=self.tenant_b,
            user_id=self.user_id,
            name="Engineering",
        )

        teams = TeamService.list_teams(
            tenant_id=self.tenant_a,
        )

        team_ids = {
            team.id
            for team in teams
        }

        assert own_team.id in team_ids
        assert len(team_ids) == 1

@pytest.mark.django_db
class TestTeamIsolation:

    def setup_method(self):
        self.tenant_a = uuid.uuid4()
        self.tenant_b = uuid.uuid4()
        self.user_id = uuid.uuid4()

    def test_cannot_update_other_tenant_team(self):
        team = TeamService.create_team(
            tenant_id=self.tenant_a,
            user_id=self.user_id,
            name="Engineering",
        )

        with pytest.raises(ResourceNotFoundError):
            TeamService.update_team(
                tenant_id=self.tenant_b,
                team_id=team.id,
                data={
                    "name": "Hacked Team",
                },
            )

        team.refresh_from_db()

        assert team.name == "Engineering"

    def test_cannot_delete_other_tenant_team(self):
        team = TeamService.create_team(
            tenant_id=self.tenant_a,
            user_id=self.user_id,
            name="Engineering",
        )

        with pytest.raises(ResourceNotFoundError):
            TeamService.delete_team(
                tenant_id=self.tenant_b,
                team_id=team.id,
            )

        assert Team.objects.filter(
            id=team.id,
        ).exists()