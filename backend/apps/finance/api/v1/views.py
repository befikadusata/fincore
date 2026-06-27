from datetime import date
from decimal import Decimal

from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.finance.api.v1.serializers import (
    LoanProductSerializer,
    LoanSerializer,
    RepaymentScheduleSerializer,
    WalletSerializer,
)
from apps.finance.models import Loan, LoanProduct, RepaymentSchedule
from apps.finance.models.wallet import Wallet
from apps.finance.services.loan_service import LoanService
from apps.finance.services.repayment_service import RepaymentService
from apps.finance.services.reporting_service import ReportingService
from core.exceptions import FinCoreError
from core.middleware.tenant import get_current_tenant
from core.permissions import HasPermission, IsTenantMember
from core.throttles import FinancialWriteThrottle


class LoanProductViewSet(viewsets.ModelViewSet):
    serializer_class = LoanProductSerializer

    def get_queryset(self):
        return LoanProduct.objects.all()

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [
                permissions.IsAuthenticated(),
                IsTenantMember(),
                HasPermission.of('loan_products:manage')(),
            ]
        return [permissions.IsAuthenticated(), IsTenantMember()]

    def perform_create(self, serializer):
        serializer.save(tenant=get_current_tenant())


class LoanViewSet(viewsets.ModelViewSet):
    serializer_class = LoanSerializer
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        return Loan.objects.all()

    def get_permissions(self):
        if self.action in ('approve', 'disburse'):
            return [
                permissions.IsAuthenticated(),
                IsTenantMember(),
                HasPermission.of('loans:manage')(),
            ]
        return [permissions.IsAuthenticated(), IsTenantMember()]

    throttle_classes = [FinancialWriteThrottle]

    def perform_create(self, serializer):
        tenant = get_current_tenant()
        product = serializer.validated_data['product']
        borrower = serializer.validated_data.get('borrower', self.request.user)
        principal_amount = serializer.validated_data['principal_amount']
        term_months = serializer.validated_data['term_months']
        idempotency_key = serializer.validated_data.get('idempotency_key', '')
        notes = serializer.validated_data.get('notes', '')

        try:
            loan = LoanService.create_loan(
                product=product,
                borrower=borrower,
                tenant=tenant,
                principal_amount=principal_amount,
                term_months=term_months,
                idempotency_key=idempotency_key,
                notes=notes,
            )
        except ValueError as exc:
            raise serializers.ValidationError({'detail': str(exc)})

        serializer.instance = loan

    @action(detail=False, methods=['get'])
    def summary(self, request):
        tenant = get_current_tenant()
        data = ReportingService.get_loan_summary(tenant)
        return Response(data)

    @action(detail=True, methods=['get'])
    def schedule(self, request, pk=None):
        loan = self.get_object()
        persisted = RepaymentSchedule.objects.filter(loan=loan).order_by('installment_number')
        if persisted.exists():
            data = {
                'loan_id': str(loan.pk),
                'principal': str(loan.principal_amount),
                'total_interest': str(loan.interest_amount),
                'total_repayable': str(loan.total_amount),
                'outstanding_balance': str(loan.outstanding_balance),
                'term_months': loan.term_months,
                'installments': RepaymentScheduleSerializer(persisted, many=True).data,
            }
        else:
            data = LoanService.compute_schedule(loan)
        return Response(data)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        loan = self.get_object()
        try:
            loan = LoanService.submit_loan(loan)
        except FinCoreError as exc:
            raise serializers.ValidationError({'detail': str(exc)})
        return Response(LoanSerializer(loan).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        loan = self.get_object()
        try:
            loan = LoanService.approve_loan(loan, request.user)
        except FinCoreError as exc:
            raise serializers.ValidationError({'detail': str(exc)})
        return Response(LoanSerializer(loan).data)

    @action(detail=True, methods=['post'])
    def disburse(self, request, pk=None):
        loan = self.get_object()
        try:
            loan = LoanService.disburse_loan(loan)
        except FinCoreError as exc:
            raise serializers.ValidationError({'detail': str(exc)})
        return Response(LoanSerializer(loan).data)

    @action(detail=True, methods=['post'])
    def repay(self, request, pk=None):
        loan = self.get_object()
        amount_raw = request.data.get('amount')
        if not amount_raw:
            raise serializers.ValidationError({'amount': 'This field is required.'})
        try:
            amount = Decimal(str(amount_raw))
        except Exception:
            raise serializers.ValidationError({'amount': 'Invalid decimal value.'})

        idempotency_key = request.data.get('idempotency_key', '')

        try:
            txn = RepaymentService.process_repayment(loan, amount, idempotency_key)
        except (FinCoreError, ValueError) as exc:
            raise serializers.ValidationError({'detail': str(exc)})

        loan.refresh_from_db()
        return Response({
            'transaction_id': str(txn.pk),
            'amount': str(txn.amount),
            'status': txn.status,
            'loan_status': loan.status,
            'outstanding_balance': str(loan.outstanding_balance),
        })


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WalletSerializer

    def get_queryset(self):
        return Wallet.objects.all()  # TenantManager auto-scopes

    def get_permissions(self):
        return [permissions.IsAuthenticated(), IsTenantMember()]

    @action(detail=True, methods=['get'])
    def statement(self, request, pk=None):
        wallet = self.get_object()

        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        start_date = None
        end_date = None

        if start_date_str:
            try:
                start_date = date.fromisoformat(start_date_str)
            except ValueError:
                raise serializers.ValidationError(
                    {'start_date': 'Invalid format. Use YYYY-MM-DD.'}
                )

        if end_date_str:
            try:
                end_date = date.fromisoformat(end_date_str)
            except ValueError:
                raise serializers.ValidationError(
                    {'end_date': 'Invalid format. Use YYYY-MM-DD.'}
                )

        data = ReportingService.get_wallet_statement(wallet, start_date, end_date)
        return Response(data)


class TrialBalanceView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsTenantMember]

    def get(self, request):
        tenant = get_current_tenant()
        data = ReportingService.get_trial_balance(tenant)
        return Response(data)
