from django.db import connection, transaction
from django.test import TestCase

class PgBouncerCompatibilityTests(TestCase):

    def test_database_connection_works(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            self.assertEqual(cursor.fetchone()[0], 1)

    def test_transaction_local_settings(self):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SET LOCAL statement_timeout = '10s'"
                )

                cursor.execute("SELECT 1")

                self.assertEqual(
                    cursor.fetchone()[0],
                    1,
                )

    def test_multiple_transactions_work(self):

        for _ in range(3):
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute("SELECT current_database()")
                    self.assertIsNotNone(cursor.fetchone()[0])

    def test_database_identity_is_correct(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT current_database(), current_user"
            )

            database_name, database_user = cursor.fetchone()

        self.assertTrue(database_name)
        self.assertTrue(database_user)