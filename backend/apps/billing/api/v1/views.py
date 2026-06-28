from django.conf import settings as django_settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsTenantMember
from core.middleware.tenant import get_current_tenant
from apps.billing.models import Subscription, Invoice
from apps.billing.api.v1.serializers import (
    SubscriptionSerializer,
    SubscribeRequestSerializer,
    ChangePlanSerializer,
    InvoiceSerializer,
)
from apps.billing.constants import BillingCycle, GatewayProvider, InvoiceStatus
from apps.billing.services.billing_service import BillingService
from apps.billing.services.gateways.chapa import ChapaGateway


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsTenantMember]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return Subscription.objects.select_related('plan').all()

    def create(self, request, *args, **kwargs):
        serializer = SubscribeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        subscription = BillingService.subscribe(
            tenant=get_current_tenant(),
            plan=data['plan'],
            billing_cycle=data.get('billing_cycle', BillingCycle.MONTHLY),
            trial_days=data.get('trial_days', 0),
        )
        return Response(SubscriptionSerializer(subscription).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='change-plan')
    def change_plan(self, request, pk=None):
        subscription = self.get_object()
        serializer = ChangePlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = BillingService.change_plan(subscription, serializer.validated_data['plan'])
        return Response(SubscriptionSerializer(updated).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        subscription = self.get_object()
        updated = BillingService.cancel_subscription(subscription)
        return Response(SubscriptionSerializer(updated).data)

    @action(detail=True, methods=['post'], url_path='generate-invoice')
    def generate_invoice(self, request, pk=None):
        subscription = self.get_object()
        invoice = BillingService.generate_invoice(subscription)
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [IsTenantMember]

    def get_queryset(self):
        return Invoice.objects.select_related('subscription__plan').all()

    @action(detail=True, methods=['post'])
    def checkout(self, request, pk=None):
        invoice = self.get_object()

        if invoice.status == InvoiceStatus.PAID:
            return Response({'error': 'Invoice already paid'}, status=status.HTTP_400_BAD_REQUEST)

        frontend_url = getattr(django_settings, 'FRONTEND_URL', 'http://localhost:3000')
        backend_url = getattr(django_settings, 'BACKEND_URL', 'http://localhost:8000')

        gateway = ChapaGateway()
        user = request.user
        customer_name = f"{user.first_name} {user.last_name}".strip() or user.email

        try:
            result = gateway.initialize_payment(
                amount=invoice.amount,
                currency=invoice.currency,
                callback_url=f"{backend_url}/api/v1/webhooks/chapa/",
                reference=invoice.invoice_number,
                customer_email=user.email,
                customer_name=customer_name,
                return_url=f"{frontend_url}/billing/success",
            )
            return Response({'checkout_url': result.checkout_url, 'reference': result.reference})
        except Exception as exc:
            return Response({'error': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
