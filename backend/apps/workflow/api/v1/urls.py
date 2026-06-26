from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.workflow.api.v1.views import (
    MyTasksViewSet,
    WorkflowDefinitionViewSet,
    WorkflowInstanceViewSet,
    WorkflowStepViewSet,
)

app_name = 'workflow'

router = DefaultRouter()
router.register('definitions', WorkflowDefinitionViewSet, basename='definition')
router.register('instances', WorkflowInstanceViewSet, basename='instance')
router.register('steps', WorkflowStepViewSet, basename='step')
router.register('my-tasks', MyTasksViewSet, basename='my-tasks')

urlpatterns = router.urls
