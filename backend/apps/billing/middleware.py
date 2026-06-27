from django.http import JsonResponse
from core.middleware.tenant import get_current_tenant


class FeatureGatingMiddleware:
    """
    Blocks access to views that declare `required_plan_feature` when the
    tenant's active subscription plan does not include that feature.
    Returns 402 when there is no active subscription, 403 for missing feature.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        view_class = getattr(view_func, 'cls', None)
        required_feature = getattr(view_class, 'required_plan_feature', None)
        if not required_feature:
            return None

        tenant = get_current_tenant()
        if not tenant:
            return None

        from apps.billing.models import Subscription
        from apps.billing.constants import SubscriptionStatus

        subscription = (
            Subscription.objects_unscoped
            .filter(
                tenant=tenant,
                status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING],
            )
            .select_related('plan')
            .first()
        )

        if subscription is None:
            return JsonResponse(
                {'error': 'Active subscription required', 'code': 'subscription_required'},
                status=402,
            )

        from apps.saas.models import PlanFeature

        if not PlanFeature.objects.filter(plan=subscription.plan, codename=required_feature).exists():
            return JsonResponse(
                {
                    'error': f'Plan does not include feature: {required_feature}',
                    'code': 'feature_not_available',
                },
                status=403,
            )

        return None
