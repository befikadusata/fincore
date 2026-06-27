from rest_framework import serializers
from apps.billing.models import Subscription, Invoice, PaymentRecord
from apps.saas.models import Plan


class SubscriptionSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)

    class Meta:
        model = Subscription
        fields = [
            'id', 'plan', 'plan_name', 'status', 'billing_cycle',
            'gateway_provider', 'gateway_subscription_id',
            'current_period_start', 'current_period_end',
            'trial_end', 'cancelled_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SubscribeRequestSerializer(serializers.Serializer):
    plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects_unscoped.all())
    billing_cycle = serializers.ChoiceField(
        choices=['monthly', 'quarterly', 'annually'], default='monthly'
    )
    trial_days = serializers.IntegerField(min_value=0, default=0)


class ChangePlanSerializer(serializers.Serializer):
    plan = serializers.PrimaryKeyRelatedField(queryset=Plan.objects_unscoped.all())


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            'id', 'subscription', 'invoice_number', 'status',
            'amount', 'currency', 'due_date', 'paid_at',
            'gateway_invoice_id', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class PaymentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRecord
        fields = [
            'id', 'invoice', 'status', 'amount', 'currency',
            'gateway_reference', 'gateway_provider', 'metadata',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields
