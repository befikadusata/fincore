from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.billing.api.v1.views import SubscriptionViewSet, InvoiceViewSet

app_name = 'billing'

router = DefaultRouter()
router.register('subscriptions', SubscriptionViewSet, basename='subscription')
router.register('invoices', InvoiceViewSet, basename='invoice')

urlpatterns = [
    path('', include(router.urls)),
]
