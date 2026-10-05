from celery import shared_task

@shared_task
def health_check_task():
    """
    Basic task used to verify that Celery
    is correctly configured and executing tasks.
    """
    return "Celery is working."