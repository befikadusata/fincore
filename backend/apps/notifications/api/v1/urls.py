from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.notifications.api.v1.views import NotificationViewSet, NotificationPreferenceViewSet

app_name = 'notifications'

notifications_router = DefaultRouter()
notifications_router.register('', NotificationViewSet, basename='notification')

preferences_router = DefaultRouter()
preferences_router.register('', NotificationPreferenceViewSet, basename='notification-preference')

urlpatterns = [
    # preferences/ must come before '' to avoid being matched as a pk
    path('preferences/', include(preferences_router.urls)),
    path('', include(notifications_router.urls)),
]
