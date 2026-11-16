from locust import HttpUser, task, between

class SaaSUser(HttpUser):

    wait_time = between(1, 3)

    @task(3)
    def list_projects(self):
        self.client.get(
            "/api/v1/projects/",
            name="List Projects",
        )

    @task(5)
    def list_tasks(self):
        self.client.get(
            "/api/v1/tasks/",
            name="List Tasks",
        )

    @task(2)
    def list_teams(self):
        self.client.get(
            "/api/v1/teams/",
            name="List Teams",
        )