import threading
from concurrent.futures import ThreadPoolExecutor
from django.db import close_old_connections
from django.test import TransactionTestCase
from apps.subscriptions.models import Subscription
from apps.subscriptions.services import SubscriptionService

class SubscriptionConcurrencyTests(TransactionTestCase):

    reset_sequences = True

    def setUp(self):
        self.subscription = Subscription.objects.create(
            # Supply your actual required model fields.
        )

    def activate_subscription(self):

        close_old_connections()

        try:
            return SubscriptionService.activate_subscription(
                self.subscription.id
            )

        finally:
            close_old_connections()

    def test_concurrent_activation(self):

        with ThreadPoolExecutor(
            max_workers=5
        ) as executor:

            futures = [
                executor.submit(self.activate_subscription)
                for _ in range(5)
            ]

            results = [
                future.result()
                for future in futures
            ]

        self.subscription.refresh_from_db()

        self.assertEqual(
            self.subscription.status,
            "ACTIVE",
        )

        self.assertEqual(len(results), 5)