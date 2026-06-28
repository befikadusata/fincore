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
    borrower_name = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            'id',
            'product',
            'product_name',
            'borrower',
            'borrower_name',
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
            'product_name',
            'borrower_name',
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

    def get_borrower_name(self, obj):
        u = obj.borrower
        name = f"{u.first_name} {u.last_name}".strip()
        return name if name else u.email

    def get_product_name(self, obj):
        return obj.product.name if obj.product else None

    def validate_principal_amount(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError('principal_amount must be greater than zero.')
        return value

    def validate_term_months(self, value):
        if value <= 0:
            raise serializers.ValidationError('term_months must be greater than zero.')
        if value > 360:
            raise serializers.ValidationError('term_months cannot exceed 360.')
        return value

    def validate_notes(self, value):
        if value and len(value) > 2000:
            raise serializers.ValidationError('notes must be 2000 characters or fewer.')
        return value


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
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = ['id', 'owner_name', 'wallet_type', 'currency', 'balance', 'status', 'created_at']
        read_only_fields = ['id', 'owner_name', 'wallet_type', 'currency', 'balance', 'status', 'created_at']

    def get_owner_name(self, obj):
        u = obj.owner
        name = f"{u.first_name} {u.last_name}".strip()
        return name if name else u.email
