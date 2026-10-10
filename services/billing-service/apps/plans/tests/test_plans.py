import uuid
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import serializers, status
from rest_framework.test import APIClient
from apps.plans.models import Plan
from apps.plans.serializers import PlanCreateSerializer, PlanResponseSerializer
from apps.plans.services import PlanService

class PlanTestDataMixin:
    """Shared data and helpers for class-based plan tests."""

    plan_data = {
        "code": "STARTER",
        "name": "Starter",
        "description": "For small teams",
        "price": "499.00",
        "currency": "INR",
        "billing_interval": Plan.BillingInterval.MONTHLY,
        "is_active": True,
        "is_public": True,
    }

    def create_plan(self, **overrides):
        data = {**self.plan_data, **overrides}
        return Plan.objects.create(
            **{
                **data,
                "price": Decimal(str(data["price"])),
            }
        )

    def create_admin_client(self):
        user_model = get_user_model()
        username_field = user_model.USERNAME_FIELD
        user_data = {
            username_field: "billing-admin@example.com"
            if username_field == "email"
            else "billing-admin",
        }
        if username_field != "email" and any(
            field.name == "email" for field in user_model._meta.fields
        ):
            user_data["email"] = "billing-admin@example.com"

        user = user_model.objects.create_superuser(
            password="test-password",
            **user_data,
        )
        client = APIClient()
        client.force_authenticate(user=user)
        return client

class PlanModelTests(PlanTestDataMixin, TestCase):
    def test_plan_uses_uuid_primary_key(self):
        plan = self.create_plan()

        self.assertIsInstance(plan.id, uuid.UUID)

    def test_plan_string_representation(self):
        plan = self.create_plan()

        self.assertEqual(str(plan), "STARTER - Starter")

    def test_plan_defaults(self):
        plan = Plan.objects.create(
            code="BASIC",
            name="Basic",
            price=Decimal("0.00"),
        )

        self.assertEqual(plan.currency, "INR")
        self.assertEqual(plan.billing_interval, Plan.BillingInterval.MONTHLY)
        self.assertTrue(plan.is_active)
        self.assertTrue(plan.is_public)

    def test_plans_are_ordered_by_price_then_name(self):
        self.create_plan(code="ZETA", name="Zeta", price="200.00")
        self.create_plan(code="ALPHA", name="Alpha", price="200.00")
        self.create_plan(code="FREE", name="Free", price="0.00")

        self.assertEqual(
            list(Plan.objects.values_list("code", flat=True)),
            ["FREE", "ALPHA", "ZETA"],
        )

    def test_plan_code_must_be_unique(self):
        self.create_plan()

        with self.assertRaises(Exception):
            self.create_plan(name="Duplicate plan")

class PlanCreateSerializerTests(PlanTestDataMixin, TestCase):
    def test_valid_plan_data_is_accepted_and_normalized(self):
        data = {**self.plan_data, "code": " starter ", "currency": "inr"}
        serializer = PlanCreateSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["code"], "STARTER")
        self.assertEqual(serializer.validated_data["currency"], "INR")
        self.assertEqual(serializer.validated_data["price"], Decimal("499.00"))

    def test_invalid_plan_code_is_rejected(self):
        for code in ("1STARTER", "A", "STARTER-PLUS", "STARTER PLUS"):
            with self.subTest(code=code):
                serializer = PlanCreateSerializer(
                    data={**self.plan_data, "code": code}
                )
                self.assertFalse(serializer.is_valid())
                self.assertIn("code", serializer.errors)

    def test_duplicate_plan_code_is_rejected(self):
        self.create_plan()
        serializer = PlanCreateSerializer(
            data={**self.plan_data, "name": "Another Starter"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("code", serializer.errors)

    def test_blank_name_is_rejected(self):
        serializer = PlanCreateSerializer(
            data={**self.plan_data, "name": "   "}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_invalid_currency_is_rejected(self):
        serializer = PlanCreateSerializer(
            data={**self.plan_data, "currency": "INDIA"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("currency", serializer.errors)

    def test_negative_price_is_rejected(self):
        serializer = PlanCreateSerializer(
            data={**self.plan_data, "price": "-1.00"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("price", serializer.errors)

    def test_invalid_billing_interval_is_rejected(self):
        serializer = PlanCreateSerializer(
            data={**self.plan_data, "billing_interval": "WEEKLY"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("billing_interval", serializer.errors)

    def test_description_can_be_blank_or_omitted(self):
        data = {**self.plan_data}
        data.pop("description")
        serializer = PlanCreateSerializer(data=data)

        self.assertTrue(serializer.is_valid(), serializer.errors)

class PlanServiceTests(PlanTestDataMixin, TestCase):
    def test_create_plan_persists_data(self):
        serializer = PlanCreateSerializer(data=self.plan_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

        plan = PlanService.create_plan(data=serializer.validated_data)

        self.assertIsNotNone(plan.id)
        self.assertEqual(plan.code, "STARTER")
        self.assertEqual(plan.price, Decimal("499.00"))

    def test_list_plans_returns_only_active_public_plans_by_default(self):
        public_plan = self.create_plan()
        self.create_plan(
            code="PRIVATE",
            name="Private",
            price="100.00",
            is_public=False,
        )
        self.create_plan(
            code="INACTIVE",
            name="Inactive",
            price="200.00",
            is_active=False,
        )

        plans = PlanService.list_plans()

        self.assertEqual(list(plans), [public_plan])

    def test_list_plans_can_include_private_and_inactive_plans(self):
        self.create_plan()
        self.create_plan(code="PRIVATE", name="Private", is_public=False)
        self.create_plan(code="INACTIVE", name="Inactive", is_active=False)

        plans = PlanService.list_plans(public_only=False)

        self.assertEqual(plans.count(), 3)

    def test_update_plan_changes_allowed_fields(self):
        plan = self.create_plan()

        updated = PlanService.update_plan(
            plan_id=plan.id,
            data={"name": "Starter Plus", "price": Decimal("799.00")},
        )

        self.assertEqual(updated.name, "Starter Plus")
        self.assertEqual(updated.price, Decimal("799.00"))
        self.assertEqual(updated.code, "STARTER")

    def test_update_plan_rejects_code_change(self):
        plan = self.create_plan()

        with self.assertRaisesRegex(ValueError, "code cannot be changed"):
            PlanService.update_plan(
                plan_id=plan.id,
                data={"code": "PRO"},
            )

    def test_update_unknown_plan_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "Plan not found"):
            PlanService.update_plan(
                plan_id=uuid.uuid4(),
                data={"name": "Missing"},
            )

    def test_delete_plan_soft_deactivates_plan(self):
        plan = self.create_plan()

        result = PlanService.delete_plan(plan_id=plan.id)

        self.assertFalse(result.is_active)
        self.assertTrue(Plan.objects.filter(pk=plan.pk).exists())

    def test_delete_unknown_plan_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "Plan not found"):
            PlanService.delete_plan(plan_id=uuid.uuid4())

    def test_get_plan_by_code_returns_public_active_plan(self):
        plan = self.create_plan()

        result = PlanService.get_plan_by_code(
            code=plan.code,
            public_only=True,
        )

        self.assertEqual(result, plan)

    def test_get_plan_by_code_can_return_private_plan_when_filter_disabled(self):
        plan = self.create_plan(is_public=False)

        result = PlanService.get_plan_by_code(
            code=plan.code,
            public_only=False,
        )

        self.assertEqual(result, plan)

    def test_get_plan_by_id_returns_plan(self):
        plan = self.create_plan()

        self.assertEqual(PlanService.get_plan_by_id(plan_id=plan.id), plan)

    def test_get_unknown_plan_by_id_raises_value_error(self):
        with self.assertRaisesRegex(ValueError, "Plan not found"):
            PlanService.get_plan_by_id(plan_id=uuid.uuid4())

class PlanResponseSerializerTests(PlanTestDataMixin, TestCase):
    def test_response_serializer_exposes_model_fields(self):
        plan = self.create_plan()
        serializer = PlanResponseSerializer(plan)

        # These assertions describe the response contract in the supplied
        # serializer; they also catch model/serializer field-name mismatches.
        self.assertEqual(serializer.data["id"], str(plan.id))
        self.assertEqual(serializer.data["code"], "STARTER")
        self.assertEqual(serializer.data["price"], Decimal("499.00"))
        self.assertIn("created_at", serializer.data)
        self.assertIn("updated_at", serializer.data)

class PublicPlanAPITests(PlanTestDataMixin, TestCase):
    def setUp(self):
        self.client = APIClient()
        self.base_url = "/api/v1/plans/"

    def test_public_list_shows_only_active_public_plans(self):
        self.create_plan()
        self.create_plan(code="PRIVATE", name="Private", is_public=False)
        self.create_plan(code="INACTIVE", name="Inactive", is_active=False)

        response = self.client.get(f"{self.base_url}list/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item["code"] for item in response.data], ["STARTER"])

    def test_public_detail_returns_plan(self):
        self.create_plan()

        response = self.client.get(f"{self.base_url}STARTER/detail/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["code"], "STARTER")

    def test_public_detail_does_not_expose_private_plan(self):
        self.create_plan(code="CUSTOM", name="Custom", is_public=False)

        response = self.client.get(f"{self.base_url}CUSTOM/detail/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class AdminPlanAPITests(PlanTestDataMixin, TestCase):
    def setUp(self):
        self.client = self.create_admin_client()
        self.base_url = "/api/v1/plans/admin/"

    def test_admin_can_create_plan(self):
        response = self.client.post(
            f"{self.base_url}create/",
            data=self.plan_data,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["code"], "STARTER")

    def test_admin_can_list_all_plans(self):
        self.create_plan()
        self.create_plan(code="PRIVATE", name="Private", is_public=False)

        response = self.client.get(f"{self.base_url}list/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_admin_can_get_plan_detail(self):
        plan = self.create_plan()

        response = self.client.get(f"{self.base_url}{plan.id}/detail/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], str(plan.id))

    def test_admin_can_update_plan(self):
        plan = self.create_plan()

        response = self.client.patch(
            f"{self.base_url}{plan.id}/update/",
            data={"name": "Starter Plus", "price": "799.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Starter Plus")

    def test_admin_can_soft_delete_plan(self):
        plan = self.create_plan()

        response = self.client.delete(f"{self.base_url}{plan.id}/delete/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        plan.refresh_from_db()
        self.assertFalse(plan.is_active)

    def test_non_admin_cannot_create_plan(self):
        client = APIClient()

        response = client.post(
            f"{self.base_url}create/",
            data=self.plan_data,
            format="json",
        )

        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED,
                                             status.HTTP_403_FORBIDDEN))
