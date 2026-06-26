from decimal import Decimal

from rest_framework import serializers

from apps.finance.models import Loan, LoanProduct, RepaymentSchedule
from apps.finance.models.wallet import Wallet


class LoanProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanProduct
        fields = [
            'id',
            'name',
            'description',
            'interest_type',
            'interest_rate',
            'compounding_periods_per_year',
            'min_term_months',
            'max_term_months',
            'min_amount',
            'max_amount',
            'currency',
            'fees_config',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        min_term = attrs.get('min_term_months', getattr(self.instance, 'min_term_months', None))
        max_term = attrs.get('max_term_months', getattr(self.instance, 'max_term_months', None))
        if min_term is not None and max_term is not None and min_term > max_term:
            raise serializers.ValidationError(
                {'max_term_months': 'max_term_months must be >= min_term_months'}
            )

        min_amount = attrs.get('min_amount', getattr(self.instance, 'min_amount', None))
        max_amount = attrs.get('max_amount', getattr(self.instance, 'max_amount', None))
        if min_amount is not None and max_amount is not None and min_amount > max_amount:
            raise serializers.ValidationError(
                {'max_amount': 'max_amount must be >= min_amount'}
            )

        rate = attrs.get('interest_rate', getattr(self.instance, 'interest_rate', None))
        if rate is not None and rate < Decimal('0'):
            raise serializers.ValidationError(
                {'interest_rate': 'interest_rate cannot be negative'}
            )

        return attrs


class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = [
            'id',
            'product',
            'borrower',
            'approved_by',
            'principal_amount',
            'interest_amount',
            'total_amount',
            'outstanding_balance',
            'term_months',
            'currency',
            'status',
            'submitted_at',
            'approved_at',
            'disbursed_at',
            'completed_at',
            'idempotency_key',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'interest_amount',
            'total_amount',
            'outstanding_balance',
            'currency',
            'status',
            'approved_by',
            'submitted_at',
            'approved_at',
            'disbursed_at',
            'completed_at',
            'created_at',
            'updated_at',
        ]


class RepaymentScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepaymentSchedule
        fields = [
            'id',
            'installment_number',
            'due_date',
            'principal_amount',
            'interest_amount',
            'total_amount',
            'amount_paid',
            'penalty_amount',
            'status',
            'paid_at',
        ]
        read_only_fields = fields


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['id', 'wallet_type', 'currency', 'balance', 'status', 'created_at']
        read_only_fields = fields
