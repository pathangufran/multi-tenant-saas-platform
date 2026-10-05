from apps.common.tasks import health_check_task

class TestCeleryTasks:

    def test_health_check_task_is_registered(self):
        assert (
            health_check_task.name
            == "apps.common.tasks.health_check_task"
        )

    def test_health_check_task_runs(self):
        result = health_check_task.apply()

        assert result.successful()
        assert result.result == "Celery is working."