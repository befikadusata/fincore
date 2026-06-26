from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.events.api.v1.views import DomainEventViewSet, EventSubscriptionViewSet

app_name = 'events'

router = DefaultRouter()
router.register('domain-events', DomainEventViewSet, basename='domain-event')
router.register('subscriptions', EventSubscriptionViewSet, basename='event-subscription')

urlpatterns = [
    path('', include(router.urls)),
]
