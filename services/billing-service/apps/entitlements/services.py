from uuid import UUID 
from django.db import transaction,IntegrityError
from .models import Feature,PlanFeature
from apps.plans.models import Plan
from apps.subscriptions.models import Subscription
from apps.usage_tracking.models import UsageRecord

class EntitlementService:
    ACTIVE_SUBSCRIPTION_STATUSES = (
        Subscription.Status.ACTIVE,
        Subscription.Status.TRIALING,
    )

    USAGE_METRICS = {
        "max_users": UsageRecord.Metric.ACTIVE_USERS,
        "max_projects": UsageRecord.Metric.PROJECTS,
        "storage_limit": UsageRecord.Metric.STORAGE_BYTES,
    }
    
    @staticmethod
    def list_features(
        *,
        active_only=True,
    ) -> Feature:
        
        features = Feature.objects.all()
        if active_only:
            features = Feature.objects.filter(
                is_active=True,
            )
            
        return features.order_by("key")
    
    @staticmethod
    def get_current_subscription(
        *,
        tenant_id: UUID,
    ) -> Subscription:
        
        return (
            Subscription.objects
            .select_related("plan")
            .get(
                tenant_id=tenant_id,
                status__in=(
                    EntitlementService.
                    ACTIVE_SUBSCRIPTION_STATUSES
                )
                .order_by("-created_at")
            )
        )
        
    @staticmethod
    @transaction.atomic
    def create_feature(
        *,
        data: dict,
    ) -> Feature:
        
        try:
            with transaction.atomic():
                return Feature.objects.create(
                    **data,
                )
        except IntegrityError:
            raise ValueError(
                "A feature with this key already exists."
            )
            
    @staticmethod
    @transaction.atomic
    def update_feature(
        *,
        feature_id: UUID,
        data: dict,
    ) -> Feature:
        
        try:
            feature = (
                Feature.objects
                .select_for_update()
                .get(id=feature_id)
            )
        except Feature.DoesNotExist:
            raise ValueError(
                "Feature not found."
            )
            
        for field,value in data.items():
            setattr(feature,field,value)
            
        try:
            with transaction.atomic():
                feature.save()
        except IntegrityError:
            raise ValueError(
                "The feature update conflicts \
                with existing data."
            )
            
        return feature
    
    @staticmethod
    def list_plan_features(
        *,
        plan_id: UUID,
    ) -> PlanFeature:
        
        return (
            PlanFeature.objects
            .select_related("plan","feature")
            .filter(plan_id=plan_id)
            .order_by("feature__key")
        )
        
    @staticmethod
    def get_plan_feature(
        *,
        plan_id: UUID,
        feature_id: UUID,
    ):
        try:
            return (
                PlanFeature.objects
                .select_related("plan","feature")
                .get(
                    plan_id=plan_id,
                    feature_id=feature_id,
                )
            )
            
        except PlanFeature.DoesNotExist:
            raise ValueError(
                "Plan feature not found."
            )
        
    @staticmethod
    @transaction.atomic
    def set_plan_feature(
        *,
        plan_id: UUID,
        feature_id: UUID,
        enabled=True,
        value=None,
    ) -> PlanFeature:
        
        try:
            plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            raise ValueError(
                "Plan not found."
            )
        
        try:    
            feature = Feature.objects.get(
                id=feature_id,
                is_active=True,
            )
        except Feature.DoesNotExist:
            raise ValueError(
                "Feature not found."
            )
            
        if not enabled and value is not None:
            raise ValueError(
                "Disabled features must not have a value."
            )
            
        EntitlementService._validate_value_type(feature,value)
        
        try:
            with transaction.atomic():
                record, _ = PlanFeature.objects.update_or_create(
                    plan=plan,
                    feature=feature,
                    defaults={
                        "enabled": enabled,
                        "value": value,
                    },
                )
                
        except IntegrityError:
            raise ValueError(
                "Could not save this plan entitlement."   
            )
            
        return record
    
    @staticmethod
    def _validate_value_type(feature, value):
        if value is None:
            return

        if feature.value_type == Feature.ValueType.BOOLEAN:
            valid = isinstance(value, bool)
        elif feature.value_type in (
            Feature.ValueType.INTEGER,
            Feature.ValueType.STORAGE_BYTES,
        ):
            valid = (
                isinstance(value, int) and 
                not isinstance(value, bool)
            )
            valid = valid and value >= 0
        else:
            valid = False

        if not valid:
            raise ValueError(
                "Value does not match feature type."
            )
            
    @staticmethod
    def get_tenant_entitlements(
        *,
        tenant_id: UUID,
    ):
        subscription = (
            EntitlementService.get_current_subscription(
                tenant_id=tenant_id,
            )
        )
        
        if subscription is None:
            return {
                "tenant_id": str(tenant_id),
                "has_subscription": False,
                "plan": None,
                "features": {},
            }
        
        assignments = (
            PlanFeature.objects
            .select_related("feature")
            .filter(
                plan=Subscription.plan,
                feature__is_active=True,
            )
        )
        
        features = {
            item.feature.key: (
                item.value if item.enabled else False
            )
            
            for item in assignments
        }
        
        return {
            "tenant_id": str(tenant_id),
            "has_subscription": True,
            "plan": {
                "id": str(subscription.plan_id),
                "code": subscription.plan.code,
                "name": subscription.plan.name,
            },
            "features": features,
        }
        
    @staticmethod
    def check_limit(
        *,
        tenant_id: UUID,
        feature_key: str,
        requested_quantity=1,
    ):
        if requested_quantity < 1:
            raise ValueError(
                "Must be at least 1."
            )
            
        subscription = (
            EntitlementService.get_current_subscription(
                tenant_id=tenant_id,
            )
        )
        
        if subscription is None:
            return {
                "allowed": False,
                "reason": "no_active_subscription",
                "feature_key": feature_key,
                "limit": None,
                "current_usage": None,
                "requested_quantity": requested_quantity,
            }

        feature = Feature.objects.get(
            key=feature_key,
            is_active=True,
        )
        
        if feature is None:
            return {
                "allowed": False,
                "reason": "unknown_feature",
                "feature_key": feature_key,
                "limit": None,
                "current_usage": None,
                "requested_quantity": requested_quantity,
            }

        assignment = PlanFeature.objects.get(
            plan=Subscription.plan,
            feature=feature,
            enabled=True,
        )
        
        if assignment is None or assignment.value is None:
            return {
                "allowed": False,
                "reason": "feature_not_entitled",
                "feature_key": feature_key,
                "limit": None,
                "current_usage": None,
                "requested_quantity": requested_quantity,
            }

        if feature_key not in EntitlementService.USAGE_METRICS:
            return {
                "allowed": False,
                "reason": "not_a_usage_limit",
                "feature_key": feature_key,
                "limit": assignment.value,
                "current_usage": None,
                "requested_quantity": requested_quantity,
            }
            
        limit = assignment.value
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            return {
                "allowed": False,
                "reason": "invalid_limit_configuration",
                "feature_key": feature_key,
                "limit": None,
                "current_usage": None,
                "requested_quantity": requested_quantity,
            }
            
        metric = EntitlementService.USAGE_METRICS[feature_key]
        usage_record = UsageRecord.objects.get(
            tenant_id=tenant_id,
            metric=metric,
        )
        current_usage = usage_record.quantity if usage_record else 0

        allowed = current_usage + requested_quantity <= limit

        return {
            "allowed": allowed,
            "reason": "within_limit" if allowed else "limit_exceeded",
            "feature_key": feature_key,
            "limit": limit,
            "current_usage": current_usage,
            "requested_quantity": requested_quantity,
            "remaining": max(limit - current_usage, 0),
        }