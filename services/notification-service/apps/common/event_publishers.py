from .async_service import AsyncIntegrationService

class EventPublisher:

    @staticmethod
    def user_invited(
        *,
        tenant_id,
        user_id,
        invitation_id=None,
    ):

        return AsyncIntegrationService.dispatch_event(
            event_type="USER_INVITED",
            tenant_id=tenant_id,
            user_id=user_id,
            payload={
                "invitation_id": (
                    str(invitation_id)
                    if invitation_id is not None
                    else None
                ),
            },
        )

    @staticmethod
    def task_assigned(
        *,
        tenant_id,
        user_id,
        task_id,
        assigned_by=None,
    ):

        return AsyncIntegrationService.dispatch_event(
            event_type="TASK_ASSIGNED",
            tenant_id=tenant_id,
            user_id=user_id,
            payload={
                "task_id": str(task_id),
                "assigned_by": (
                    str(assigned_by)
                    if assigned_by is not None
                    else None
                ),
            },
        )

    @staticmethod
    def task_completed(
        *,
        tenant_id,
        user_id,
        task_id,
        completed_by=None,
    ):

        return AsyncIntegrationService.dispatch_event(
            event_type="TASK_COMPLETED",
            tenant_id=tenant_id,
            user_id=user_id,
            payload={
                "task_id": str(task_id),
                "completed_by": (
                    str(completed_by)
                    if completed_by is not None
                    else None
                ),
            },
        )

    @staticmethod
    def password_reset(
        *,
        user_id,
    ):

        return AsyncIntegrationService.dispatch_event(
            event_type="PASSWORD_RESET",
            tenant_id=None,
            user_id=user_id,
            payload={},
        )

    @staticmethod
    def subscription_created(
        *,
        tenant_id,
        user_id=None,
        subscription_id=None,
    ):

        return AsyncIntegrationService.dispatch_event(
            event_type="SUBSCRIPTION_CREATED",
            tenant_id=tenant_id,
            user_id=user_id,
            payload={
                "subscription_id": (
                    str(subscription_id)
                    if subscription_id is not None
                    else None
                ),
            },
        )

    @staticmethod
    def payment_failed(
        *,
        tenant_id,
        user_id=None,
        payment_id=None,
    ):

        return AsyncIntegrationService.dispatch_event(
            event_type="PAYMENT_FAILED",
            tenant_id=tenant_id,
            user_id=user_id,
            payload={
                "payment_id": (
                    str(payment_id)
                    if payment_id is not None
                    else None
                ),
            },
        )

    @staticmethod
    def report_ready(
        *,
        tenant_id,
        user_id=None,
        report_id=None,
    ):

        return AsyncIntegrationService.dispatch_event(
            event_type="REPORT_READY",
            tenant_id=tenant_id,
            user_id=user_id,
            payload={
                "report_id": (
                    str(report_id)
                    if report_id is not None
                    else None
                ),
            },
        )