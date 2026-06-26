from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.events.api.v1.serializers import DomainEventSerializer, EventSubscriptionSerializer
from apps.events.models import DomainEvent, EventSubscription
from apps.events.tasks import dispatch_event
from core.permissions import HasPermission


class DomainEventViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = DomainEventSerializer
    permission_classes = [HasPermission.of('events:read')]

    def get_queryset(self):
        qs = DomainEvent.objects.all()
        status = self.request.query_params.get('status')
        event_type = self.request.query_params.get('event_type')
        if status:
            qs = qs.filter(status=status)
        if event_type:
            qs = qs.filter(event_type=event_type)
        return qs

    @action(detail=True, methods=['post'], url_path='retry')
    def retry(self, request, pk=None):
        event = self.get_object()
        dispatch_event.apply_async(args=[str(event.id)])
        return Response({'status': 'queued'})


class EventSubscriptionViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = EventSubscriptionSerializer
    queryset = EventSubscription.objects.all()
    permission_classes = [HasPermission.of('events:manage')]
