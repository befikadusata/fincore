"""
Tests for task 2.4 — Finance ↔ Events ↔ Workflow wiring.

Covers:
  - LoanService emits the expected domain events
  - handle_loan_submitted instantiates a workflow
  - handle_workflow_completed drives loan to APPROVED or REJECTED
  - handle_loan_approved auto-disburses the loan
  - RepaymentService emits repayment.received (and loan.completed on final payment)
  - check_overdue emits loan.overdue per affected loan
"""
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

from apps.events.constants import EventType
from apps.events.models import DomainEvent, EventSubscription
from apps.events.registry import EventRegistry
from apps.events.services.event_bus import EventBus
from apps.finance.constants import LoanStatus, RepaymentStatus
from apps.finance.handlers import handle_loan_approved
from apps.finance.services.loan_service import LoanService
from apps.finance.services.repayment_service import RepaymentService
from apps.saas.models import Tenant, User
from apps.workflow.constants import WorkflowStatus
from apps.workflow.handlers import handle_loan_submitted, handle_workflow_completed
from apps.workflow.models import WorkflowDefinition, WorkflowInstance
from apps.workflow.services.workflow_service import WorkflowService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_registry():
    EventRegistry.clear()
    yield
    EventRegistry.clear()


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(name='Wire Bank', slug='wire-bank')


@pytest.fixture
def borrower(db):
    return User.objects.create_user(email='borrower@wire.com', password='pw')


@pytest.fixture
def product(db, tenant):
    from apps.finance.models.loan_product import LoanProduct
    from apps.finance.constants import InterestType
    return LoanProduct.objects_unscoped.create(
        tenant=tenant,
        name='Test Product',
        interest_type=InterestType.FLAT,
        interest_rate=Decimal('10.00'),
        min_amount=Decimal('100'),
        max_amount=Decimal('10000'),
        min_term_months=1,
        max_term_months=12,
        currency='ETB',
        fees_config={},
    )


@pytest.fixture
def loan(db, tenant, borrower, product):
    return LoanService.create_loan(
        product=product,
        borrower=borrower,
        tenant=tenant,
        principal_amount=Decimal('1000'),
        term_months=3,
    )


@pytest.fixture
def loan_definition(db, tenant):
    return WorkflowService.create_definition(
        name='Loan Approval',
        trigger_event='loan.submitted',
        config={
            'steps': [
                {'order': 1, 'name': 'Review', 'type': 'approval', 'conditions': [], 'auto_execute': False},
            ]
        },
        tenant=tenant,
    )


# ---------------------------------------------------------------------------
# Event emission from LoanService
# ---------------------------------------------------------------------------

class TestLoanServiceEmitsEvents:
    def test_submit_emits_loan_submitted(self, db, loan):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            LoanService.submit_loan(loan)
        assert DomainEvent.objects_unscoped.filter(
            event_type=EventType.LOAN_SUBMITTED,
            entity_id=str(loan.pk),
        ).exists()

    def test_approve_emits_loan_approved(self, db, loan):
        LoanService.submit_loan(loan)
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            LoanService.approve_loan(loan)
        assert DomainEvent.objects_unscoped.filter(
            event_type=EventType.LOAN_APPROVED,
            entity_id=str(loan.pk),
        ).exists()

    def test_reject_emits_loan_rejected(self, db, loan):
        LoanService.submit_loan(loan)
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            LoanService.reject_loan(loan)
        assert DomainEvent.objects_unscoped.filter(
            event_type=EventType.LOAN_REJECTED,
            entity_id=str(loan.pk),
        ).exists()

    def test_default_emits_loan_defaulted(self, db, loan):
        LoanService.submit_loan(loan)
        LoanService.approve_loan(loan)
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            with patch('apps.finance.services.repayment_service._emit_repayment_events'):
                LoanService.disburse_loan(loan)
        loan.refresh_from_db()
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            LoanService.default_loan(loan)
        assert DomainEvent.objects_unscoped.filter(
            event_type=EventType.LOAN_DEFAULTED,
            entity_id=str(loan.pk),
        ).exists()

    def test_disburse_emits_loan_disbursed(self, db, loan):
        LoanService.submit_loan(loan)
        LoanService.approve_loan(loan)
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            with patch('apps.finance.services.repayment_service._emit_repayment_events'):
                LoanService.disburse_loan(loan)
        assert DomainEvent.objects_unscoped.filter(
            event_type=EventType.LOAN_DISBURSED,
            entity_id=str(loan.pk),
        ).exists()

    def test_approve_accepts_none_approver(self, db, loan):
        LoanService.submit_loan(loan)
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            result = LoanService.approve_loan(loan, approver=None)
        assert result.approved_by is None
        assert result.status == LoanStatus.APPROVED


# ---------------------------------------------------------------------------
# handle_loan_submitted
# ---------------------------------------------------------------------------

class TestHandleLoanSubmitted:
    def _make_event(self, loan, tenant):
        evt = MagicMock()
        evt.tenant_id = tenant.id
        evt.tenant = tenant
        evt.entity_id = str(loan.pk)
        evt.payload = {'principal_amount': str(loan.principal_amount)}
        return evt

    def test_instantiates_workflow_when_definition_exists(self, db, loan, tenant, loan_definition):
        event = self._make_event(loan, tenant)
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            handle_loan_submitted(event)
        assert WorkflowInstance.objects_unscoped.filter(
            entity_type='Loan',
            entity_id=str(loan.pk),
        ).exists()

    def test_noop_when_no_definition(self, db, loan, tenant):
        event = self._make_event(loan, tenant)
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            handle_loan_submitted(event)  # No definition — should not raise
        assert not WorkflowInstance.objects_unscoped.filter(entity_id=str(loan.pk)).exists()

    def test_uses_latest_active_definition(self, db, loan, tenant, loan_definition):
        newer = WorkflowService.create_definition(
            name='Loan Approval',
            trigger_event='loan.submitted',
            config={'steps': [{'order': 1, 'name': 'Review', 'type': 'approval', 'conditions': [], 'auto_execute': False}]},
            tenant=tenant,
        )
        event = self._make_event(loan, tenant)
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            handle_loan_submitted(event)
        instance = WorkflowInstance.objects_unscoped.get(entity_id=str(loan.pk))
        assert instance.definition == newer

    def test_inactive_definition_is_ignored(self, db, loan, tenant, loan_definition):
        loan_definition.is_active = False
        loan_definition.save()
        event = self._make_event(loan, tenant)
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            handle_loan_submitted(event)
        assert not WorkflowInstance.objects_unscoped.filter(entity_id=str(loan.pk)).exists()


# ---------------------------------------------------------------------------
# handle_workflow_completed
# ---------------------------------------------------------------------------

class TestHandleWorkflowCompleted:
    def _make_event(self, loan, instance, outcome):
        evt = MagicMock()
        evt.tenant_id = instance.tenant_id
        evt.tenant = instance.tenant
        evt.entity_type = 'Loan'
        evt.entity_id = str(loan.pk)
        evt.payload = {
            'outcome': outcome,
            'instance_id': str(instance.id),
            'definition_id': str(instance.definition_id),
            'definition_name': instance.definition.name,
        }
        return evt

    @pytest.fixture
    def submitted_loan_with_instance(self, db, loan, tenant, loan_definition):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            LoanService.submit_loan(loan)
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            instance = WorkflowService.instantiate(
                definition=loan_definition,
                entity_type='Loan',
                entity_id=str(loan.pk),
                tenant=tenant,
            )
        return loan, instance

    def test_approved_outcome_transitions_loan_to_approved(
        self, db, submitted_loan_with_instance
    ):
        loan, instance = submitted_loan_with_instance
        event = self._make_event(loan, instance, outcome='completed')
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            handle_workflow_completed(event)
        loan.refresh_from_db()
        assert loan.status == LoanStatus.APPROVED

    def test_rejected_outcome_transitions_loan_to_rejected(
        self, db, submitted_loan_with_instance
    ):
        loan, instance = submitted_loan_with_instance
        event = self._make_event(loan, instance, outcome='rejected')
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            handle_workflow_completed(event)
        loan.refresh_from_db()
        assert loan.status == LoanStatus.REJECTED

    def test_ignores_non_loan_entities(self, db, tenant, loan_definition):
        evt = MagicMock()
        evt.entity_type = 'SomeOtherModel'
        evt.entity_id = 'irrelevant'
        evt.payload = {'outcome': 'completed', 'definition_id': str(loan_definition.id)}
        handle_workflow_completed(evt)  # Should not raise

    def test_ignores_non_loan_submitted_definition(self, db, loan, tenant):
        other_def = WorkflowService.create_definition(
            name='Something Else',
            trigger_event='something.else',
            config={'steps': [{'order': 1, 'name': 'S', 'type': 'approval', 'conditions': [], 'auto_execute': False}]},
            tenant=tenant,
        )
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            LoanService.submit_loan(loan)
        instance = WorkflowInstance.objects_unscoped.create(
            tenant=tenant,
            definition=other_def,
            entity_type='Loan',
            entity_id=str(loan.pk),
            status=WorkflowStatus.COMPLETED,
            context={},
        )
        evt = MagicMock()
        evt.entity_type = 'Loan'
        evt.entity_id = str(loan.pk)
        evt.payload = {'outcome': 'completed', 'definition_id': str(other_def.id)}
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            handle_workflow_completed(evt)
        loan.refresh_from_db()
        assert loan.status == LoanStatus.SUBMITTED  # Unchanged


# ---------------------------------------------------------------------------
# handle_loan_approved (auto-disburse)
# ---------------------------------------------------------------------------

class TestHandleLoanApproved:
    def _make_event(self, loan):
        evt = MagicMock()
        evt.entity_id = str(loan.pk)
        return evt

    def test_disburses_approved_loan(self, db, loan):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            LoanService.submit_loan(loan)
            LoanService.approve_loan(loan)
        event = self._make_event(loan)
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            with patch('apps.finance.services.repayment_service._emit_repayment_events'):
                handle_loan_approved(event)
        loan.refresh_from_db()
        assert loan.status == LoanStatus.ACTIVE

    def test_noop_when_loan_not_approved(self, db, loan):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            LoanService.submit_loan(loan)
        event = self._make_event(loan)
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            handle_loan_approved(event)  # Loan is SUBMITTED, not APPROVED → no-op
        loan.refresh_from_db()
        assert loan.status == LoanStatus.SUBMITTED


# ---------------------------------------------------------------------------
# RepaymentService event emissions
# ---------------------------------------------------------------------------

class TestRepaymentEventEmissions:
    @pytest.fixture
    def active_loan(self, db, loan, tenant, borrower):
        from apps.finance.models.account import Account
        from apps.finance.models.wallet import Wallet
        from apps.finance.services.wallet_service import WalletService
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            LoanService.submit_loan(loan)
            LoanService.approve_loan(loan)
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            with patch('apps.finance.services.repayment_service._emit_repayment_events'):
                LoanService.disburse_loan(loan)
        loan.refresh_from_db()
        # Top up the wallet so the borrower can repay principal + interest
        wallet = Wallet.objects_unscoped.get(tenant=tenant, owner=borrower)
        cash = Account.objects_unscoped.get(tenant=tenant, code='1000')
        WalletService.credit(wallet, Decimal('500'), 'TOP-UP', source_account=cash)
        return loan

    def test_process_repayment_emits_repayment_received(self, db, active_loan):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            RepaymentService.process_repayment(active_loan, Decimal('100'))
        assert DomainEvent.objects_unscoped.filter(
            event_type=EventType.REPAYMENT_RECEIVED,
            entity_id=str(active_loan.pk),
        ).exists()

    def test_full_repayment_emits_loan_completed(self, db, active_loan):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            RepaymentService.process_repayment(active_loan, active_loan.outstanding_balance)
        assert DomainEvent.objects_unscoped.filter(
            event_type=EventType.LOAN_COMPLETED,
            entity_id=str(active_loan.pk),
        ).exists()

    def test_check_overdue_emits_loan_overdue(self, db, active_loan):
        from django.utils import timezone
        from datetime import timedelta
        from apps.finance.models.repayment_schedule import RepaymentSchedule
        past = timezone.now().date() - timedelta(days=5)
        RepaymentSchedule.objects_unscoped.filter(loan=active_loan).update(due_date=past)
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            RepaymentService.check_overdue()
        assert DomainEvent.objects_unscoped.filter(
            event_type=EventType.LOAN_OVERDUE,
            entity_id=str(active_loan.pk),
        ).exists()

    def test_check_overdue_no_events_when_nothing_overdue(self, db, active_loan):
        with patch('apps.events.tasks.dispatch_event.apply_async'):
            RepaymentService.check_overdue()
        assert not DomainEvent.objects_unscoped.filter(
            event_type=EventType.LOAN_OVERDUE,
        ).exists()
