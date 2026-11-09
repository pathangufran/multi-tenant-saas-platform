from django.test import SimpleTestCase
from apps.event_consumers.exceptions import (
    EventHandlerAlreadyRegisteredError,
)
from apps.event_consumers.registry import EventHandlerRegistry

class EventHandlerRegistryTests(SimpleTestCase):

    def setUp(self):
        self.registry = EventHandlerRegistry()

    def test_register_handler(self):

        def handler(event):
            return True

        self.registry.register(
            "project.created",
            handler,
        )

        self.assertTrue(
            self.registry.has_handler("project.created")
        )

    def test_get_registered_handler(self):

        def handler(event):
            return True

        self.registry.register(
            "project.created",
            handler,
        )

        self.assertIs(
            self.registry.get_handler("project.created"),
            handler,
        )

    def test_unregistered_handler_returns_none(self):

        self.assertIsNone(
            self.registry.get_handler("project.created")
        )

    def test_duplicate_registration_is_rejected(self):

        def handler(event):
            return True

        self.registry.register(
            "project.created",
            handler,
        )

        with self.assertRaises(
            EventHandlerAlreadyRegisteredError
        ):
            self.registry.register(
                "project.created",
                handler,
            )

    def test_non_callable_handler_is_rejected(self):

        with self.assertRaises(ValueError):
            self.registry.register(
                "project.created",
                "not-callable",
            )

    def test_empty_event_type_is_rejected(self):

        with self.assertRaises(ValueError):
            self.registry.register(
                "",
                lambda event: True,
            )

    def test_unregister_handler(self):

        self.registry.register(
            "project.created",
            lambda event: True,
        )

        self.registry.unregister("project.created")

        self.assertFalse(
            self.registry.has_handler("project.created")
        )

    def test_clear_registry(self):

        self.registry.register(
            "project.created",
            lambda event: True,
        )

        self.registry.register(
            "task.created",
            lambda event: True,
        )

        self.registry.clear()

        self.assertEqual(
            self.registry.registered_event_types(),
            (),
        )

    def test_registered_event_types(self):

        self.registry.register(
            "project.created",
            lambda event: True,
        )

        self.registry.register(
            "task.created",
            lambda event: True,
        )

        self.assertEqual(
            set(self.registry.registered_event_types()),
            {"project.created", "task.created"},
        )