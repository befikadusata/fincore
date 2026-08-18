"""Seed a complete demo dataset for FinCore.

Run with:
    docker compose -f docker/docker-compose.yml exec django python seed_demo.py
    docker compose -f docker/docker-compose.yml exec django python seed_demo.py --reset

Every screen in the dashboard is meant to have something on it after this runs:
team members and roles, a loan portfolio spread across the whole lifecycle,
wallets with real ledger movement, pending approvals in My Tasks, notifications,
invoices, and an audit trail attributed to named people.

`--reset` deletes the demo tenant's own data and rebuilds it. Without it the
script is additive and idempotent, which is safe but means a loan you advanced
by hand during a previous demo stays advanced — use `--reset` before a rehearsed
run so the starting state is exactly the one you practised on.
"""
import argparse
import os
from contextlib import contextmanager
from datetime import timedelta
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.core.management import call_command
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.events.constants import EventStatus
from apps.events.models import DomainEvent
from apps.billing.constants import (
    BillingCycle, GatewayProvider, InvoiceStatus, PaymentStatus, SubscriptionStatus,
)
from apps.billing.models.invoice import Invoice
from apps.billing.models.payment_record import PaymentRecord
from apps.billing.models.subscription import Subscription
from apps.finance.constants import (
    AccountCategory, AccountType, InterestType, LoanStatus, RepaymentStatus, WalletType,
)
from apps.finance.models.account import Account
from apps.finance.models.ledger_entry import LedgerEntry
from apps.finance.models.loan import Loan, Transaction
from apps.finance.models.loan_product import LoanProduct
from apps.finance.models.repayment_schedule import RepaymentSchedule
from apps.finance.models.wallet import Wallet
from apps.finance.services.loan_service import LoanService
from apps.finance.services.repayment_service import RepaymentService
from apps.finance.services.wallet_service import WalletService
from apps.notifications.models.notification import Notification
from apps.notifications.models.notification_preference import NotificationPreference
from apps.notifications.services.notification_service import NotificationService
from apps.saas.models import (
    Membership, Permission, Plan, PlanFeature, Role, RolePermission, User,
)
from apps.saas.services.rbac import RBACService
from apps.saas.services.tenant import TenantService
from apps.workflow.models import WorkflowDefinition, WorkflowInstance, WorkflowStep
from apps.workflow.services.workflow_service import WorkflowService
from core.middleware.audit import clear_audit_context, set_audit_context
from core.middleware.tenant import set_current_tenant

parser = argparse.ArgumentParser(description="Seed the FinCore demo dataset.")
parser.add_argument("--email", default="me@example.com", help="Owner account email.")
parser.add_argument(
    "--reset",
    action="store_true",
    help="Delete the demo tenant's data first and rebuild it from scratch.",
)
args = parser.parse_args()

EMAIL = args.email
DEMO_PASSWORD = "demo1234"  # Development fixture only — never used outside seeding.
TENANT_SLUG = "demo-lending-co"


# ── Async dispatch ────────────────────────────────────────────────────────────
# This script performs every state change itself and instantiates the workflows
# it wants, so the Celery fan-out behind each domain event has nothing left to
# contribute here — and three ways to get it wrong:
#
#   * it races `--reset`, which deletes the very loans the worker is mid-way
#     through handling, and the two deadlock on finance_loan;
#   * with the worker down, on_commit still enqueues, so the run banks a backlog
#     that replays against deleted rows the moment a worker comes back;
#   * handle_loan_submitted builds a workflow instance for every loan.submitted
#     it sees, duplicating the instances created explicitly further down.
#
# Suppressing dispatch makes a seed run deterministic whether or not a worker is
# up. The events themselves are still written, so the events screen has history.
from apps.events.tasks import dispatch_event

dispatch_event.apply_async = lambda *a, **kw: None


def settle_pending_events(tenant, note):
    """Mark the tenant's un-dispatched events processed.

    Nothing will ever consume them: dispatch is suppressed above, so they would
    sit PENDING indefinitely until something re-dispatched them — and a
    loan.submitted replayed hours later builds a *second* workflow instance for
    a loan the demo has long since moved past, which is where the stray tasks
    with no borrower name in My Tasks come from. Settling them also disarms any
    message still queued from an earlier run, because dispatch_event returns
    early on an event that is already PROCESSED.
    """
    settled = DomainEvent.objects_unscoped.filter(
        tenant=tenant, status__in=(EventStatus.PENDING, EventStatus.PROCESSING),
    ).update(status=EventStatus.PROCESSED, processed_at=timezone.now())
    if settled:
        print(f"  Settled {settled} un-dispatched event(s) {note}")
    return settled


def warn_if_worker_live():
    """Say so, loudly, if a Celery worker is up when --reset starts.

    The delete below takes out most of the tenant's tables at once. A worker
    part-way through a handler holds row locks on finance_loan and the two
    deadlock — Postgres kills one of them and the reset dies half-done. Nothing
    this script can do prevents that from outside the worker, so the honest
    move is to name the problem and the fix rather than fail cryptically.
    """
    try:
        from config.celery import app as celery_app
        replies = celery_app.control.ping(timeout=1.0)
    except Exception:
        return
    if not replies:
        return
    names = ", ".join(sorted(k for reply in replies for k in reply))
    print(f"  ! A Celery worker is running ({names}).")
    print("  ! It can hold locks on the rows this reset deletes, and the two")
    print("  ! can deadlock on finance_loan. If that happens, stop the workers:")
    print("  !   docker compose -f docker/docker-compose.yml stop celery_beat celery_worker")
    print("  ! then re-run this script and start them again afterwards.")


def heading(text):
    print(f"\n{text}")


@contextmanager
def acting_as(actor):
    """Attribute everything written inside the block to a real person.

    The audit decorator reads its actor from the request-scoped context that
    AuditMiddleware normally fills in. A seed script has no request, so without
    this every entry would land as actor_type=system with a blank actor — and
    the audit screen is a lot less convincing when nobody did anything.
    """
    set_audit_context({
        "user_id": actor.id,
        "ip_address": "10.4.1.20",
        "user_agent": "FinCore Seed Script",
    })
    try:
        yield
    finally:
        clear_audit_context()


def get_or_create_user(email, first_name, last_name):
    user = User.objects.filter(email=email).first()
    if user:
        return user, False
    user = User.objects.create_user(
        email=email, password=DEMO_PASSWORD,
        first_name=first_name, last_name=last_name,
    )
    return user, True


# ── Platform catalogue (global, not tenant-scoped) ────────────────────────────
heading("Seeding permissions...")
call_command("seed_permissions", verbosity=0)
print(f"  {Permission.objects.count()} permissions")

heading("Seeding billing plans...")
PLANS = [
    dict(
        name="Starter", slug="starter", monthly_price=0, annual_price=0,
        description="Up to 3 members, 50 loans/month",
        features=[("Loan lifecycle", "loan_lifecycle"), ("Basic reporting", "basic_reporting")],
    ),
    dict(
        name="Growth", slug="growth", monthly_price=500, annual_price=5000,
        description="Up to 10 members, 500 loans/month",
        features=[
            ("Loan lifecycle", "loan_lifecycle"),
            ("Advanced reporting", "advanced_reporting"),
            ("Workflow automation", "workflow_automation"),
            ("Audit trail", "audit_trail"),
        ],
    ),
    dict(
        name="Enterprise", slug="enterprise", monthly_price=2000, annual_price=20000,
        description="Unlimited members and loans",
        features=[
            ("Everything in Growth", "everything_growth"),
            ("Priority support", "priority_support"),
            ("Custom integrations", "custom_integrations"),
            ("SLA guarantee", "sla_guarantee"),
        ],
    ),
]
plans = {}
for spec in PLANS:
    features = spec.pop("features")
    plan = Plan.objects.filter(slug=spec["slug"]).first()
    if not plan:
        plan = Plan.objects.create(**spec)
        for fname, fcode in features:
            PlanFeature.objects.get_or_create(plan=plan, codename=fcode, defaults={"name": fname})
        print(f"  Created: {plan.name}")
    else:
        print(f"  Exists : {plan.name}")
    plans[plan.slug] = plan


# ── Owner and tenant ──────────────────────────────────────────────────────────
heading(f"Owner account: {EMAIL}")
owner, owner_created = get_or_create_user(EMAIL, "Bethel", "Assefa")
print(f"  {'Created' if owner_created else 'Found  '}: {EMAIL}")

tenant = Membership.objects.filter(user=owner).select_related("tenant").first()
tenant = tenant.tenant if tenant else None
if tenant is None:
    tenant = TenantService.create_tenant(
        name="Demo Lending Co", slug=TENANT_SLUG, owner_user=owner,
    )
    print(f"  Created tenant: {tenant.name}")
else:
    print(f"  Using tenant  : {tenant.name} ({tenant.slug})")

set_current_tenant(tenant)


# ── Reset ─────────────────────────────────────────────────────────────────────
if args.reset:
    heading("Resetting demo tenant data...")
    warn_if_worker_live()
    with transaction.atomic():
        # Ordered by dependency: ledger and transactions reference accounts and
        # loans via PROTECT, so they have to go before the rows they point at.
        # Domain events go too. They are the seed's own audit of what it did,
        # but a surviving PENDING event is a live instruction to rebuild a
        # workflow for a loan this block is about to delete.
        DomainEvent.objects_unscoped.filter(tenant=tenant).delete()
        WorkflowStep.objects_unscoped.filter(tenant=tenant).delete()
        WorkflowInstance.objects_unscoped.filter(tenant=tenant).delete()
        WorkflowDefinition.objects_unscoped.filter(tenant=tenant).delete()
        Notification.objects_unscoped.filter(tenant=tenant).delete()
        NotificationPreference.objects_unscoped.filter(tenant=tenant).delete()
        PaymentRecord.objects_unscoped.filter(tenant=tenant).delete()
        Invoice.objects_unscoped.filter(tenant=tenant).delete()
        Subscription.objects_unscoped.filter(tenant=tenant).delete()
        LedgerEntry.objects_unscoped.filter(tenant=tenant).delete()
        Transaction.objects_unscoped.filter(tenant=tenant).delete()
        RepaymentSchedule.objects_unscoped.filter(tenant=tenant).delete()
        Loan.objects_unscoped.filter(tenant=tenant).delete()
        Wallet.objects_unscoped.filter(tenant=tenant).delete()
        LoanProduct.objects_unscoped.filter(tenant=tenant).delete()
        Account.objects_unscoped.filter(tenant=tenant).delete()
        # AuditLog blocks delete() on the instance to keep the trail append-only;
        # a queryset delete bypasses that, which is the point of an explicit reset.
        AuditLog.objects.filter(tenant=tenant).delete()
    print("  Cleared loans, ledger, wallets, workflow, events, notifications, invoices, audit")


# ── Team ──────────────────────────────────────────────────────────────────────
heading("Building the team...")
ROLES = [
    ("owner", "Owner", None),  # None = every permission
    ("loan_officer", "Loan Officer", [
        "loans:manage", "loan_products:manage", "workflow:read",
    ]),
    ("credit_analyst", "Credit Analyst", [
        "loans:manage", "workflow:read", "events:read",
    ]),
    ("finance_manager", "Finance Manager", [
        "loans:manage", "workflow:read", "workflow:manage", "events:read", "audit:read",
    ]),
    ("auditor", "Auditor", [
        "audit:read", "events:read", "workflow:read",
    ]),
]
roles = {}
for slug, name, codenames in ROLES:
    role, created = Role.objects.get_or_create(tenant=tenant, slug=slug, defaults={"name": name})
    perms = (
        Permission.objects.all()
        if codenames is None
        else Permission.objects.filter(codename__in=codenames)
    )
    RolePermission.objects.bulk_create(
        [RolePermission(role=role, permission=p) for p in perms], ignore_conflicts=True,
    )
    roles[slug] = role
    print(f"  {'Created' if created else 'Exists '}: {name} ({perms.count()} permissions)")

STAFF = [
    ("officer@example.com", "Selam", "Tadesse", "loan_officer"),
    ("analyst@example.com", "Nahom", "Girma", "credit_analyst"),
    ("finance@example.com", "Rahel", "Mekonnen", "finance_manager"),
    ("auditor@example.com", "Yared", "Desta", "auditor"),
]
staff = {}
with acting_as(owner):
    owner_membership = Membership.objects.get(user=owner, tenant=tenant)
    roles["owner"].membership.add(owner_membership)
    # The owner also sits in the two approval roles so that a demo driven from
    # the owner login still has items waiting in My Tasks.
    for slug in ("credit_analyst", "finance_manager"):
        RBACService.assign_role(owner, tenant, roles[slug])

    for email, first, last, role_slug in STAFF:
        member, created = get_or_create_user(email, first, last)
        Membership.objects.get_or_create(
            user=member, tenant=tenant, defaults={"status": "active"},
        )
        RBACService.assign_role(member, tenant, roles[role_slug])
        staff[role_slug] = member
        print(f"  {'Created' if created else 'Exists '}: {email} → {role_slug}")

officer = staff["loan_officer"]
analyst = staff["credit_analyst"]
finance_manager = staff["finance_manager"]


# ── Borrowers ─────────────────────────────────────────────────────────────────
heading("Creating borrowers...")
BORROWERS = [
    ("almaz@borrower.demo", "Almaz", "Tesfaye"),
    ("dawit@borrower.demo", "Dawit", "Bekele"),
    ("hanna@borrower.demo", "Hanna", "Girma"),
    ("yonas@borrower.demo", "Yonas", "Alemu"),
    ("meron@borrower.demo", "Meron", "Haile"),
    ("kebede@borrower.demo", "Kebede", "Worku"),
]
borrowers = {}
for email, first, last in BORROWERS:
    person, _ = get_or_create_user(email, first, last)
    borrowers[first.lower()] = person
print(f"  {len(borrowers)} borrowers ready")


# ── Chart of accounts ─────────────────────────────────────────────────────────
heading("Creating chart of accounts...")
ACCOUNTS = [
    ("Cash & Bank",         AccountType.ASSET,     AccountCategory.CASH,                "1000"),
    ("Loan Receivable",     AccountType.ASSET,     AccountCategory.LOAN_RECEIVABLE,     "1100"),
    ("Interest Receivable", AccountType.ASSET,     AccountCategory.INTEREST_RECEIVABLE, "1200"),
    ("Fee Receivable",      AccountType.ASSET,     AccountCategory.FEE_RECEIVABLE,      "1300"),
    ("Borrower Wallet",     AccountType.LIABILITY, AccountCategory.BORROWER_WALLET,     "2000"),
    ("Interest Revenue",    AccountType.REVENUE,   AccountCategory.INTEREST_REVENUE,    "4000"),
    ("Fee Revenue",         AccountType.REVENUE,   AccountCategory.FEE_REVENUE,         "4100"),
    ("Penalty Revenue",     AccountType.REVENUE,   AccountCategory.PENALTY_REVENUE,     "4200"),
]
for name, acct_type, category, code in ACCOUNTS:
    # Keyed on code, not category: WalletService files every per-wallet account
    # under BORROWER_WALLET too, so a category lookup stops being unique the
    # moment a single wallet exists.
    Account.objects.get_or_create(
        tenant=tenant, code=code,
        defaults={"name": name, "account_type": acct_type, "category": category},
    )
cash_account = Account.objects_unscoped.get(tenant=tenant, code="1000")
print(f"  {len(ACCOUNTS)} accounts ready")


# ── Loan products ─────────────────────────────────────────────────────────────
heading("Creating loan products...")
PRODUCTS = [
    dict(
        name="Personal Micro Loan",
        description="Short-term personal loan for small needs",
        interest_type=InterestType.FLAT, interest_rate=Decimal("15.00"),
        min_term_months=1, max_term_months=12,
        min_amount=Decimal("1000.00"), max_amount=Decimal("50000.00"),
        fees_config={"origination_fee_pct": 1.5, "penalty_rate_pct": 2.0},
    ),
    dict(
        name="Business Growth Loan",
        description="Medium-term loan for business expansion",
        interest_type=InterestType.REDUCING_BALANCE, interest_rate=Decimal("18.00"),
        min_term_months=3, max_term_months=24,
        min_amount=Decimal("10000.00"), max_amount=Decimal("500000.00"),
        fees_config={"origination_fee_pct": 2.0, "insurance_fee_pct": 0.5, "penalty_rate_pct": 2.5},
    ),
    dict(
        name="Agriculture Seasonal Loan",
        description="Seasonal financing for farmers",
        interest_type=InterestType.FLAT, interest_rate=Decimal("12.00"),
        min_term_months=3, max_term_months=9,
        min_amount=Decimal("5000.00"), max_amount=Decimal("200000.00"),
        fees_config={"penalty_rate_pct": 1.0},
    ),
]
products = {}
for spec in PRODUCTS:
    product, created = LoanProduct.objects.get_or_create(
        tenant=tenant, name=spec["name"], defaults=spec,
    )
    products[spec["name"]] = product
    print(f"  {'Created' if created else 'Exists '}: {product.name}")

micro = products["Personal Micro Loan"]
business = products["Business Growth Loan"]
agri = products["Agriculture Seasonal Loan"]


# ── Operating wallets ─────────────────────────────────────────────────────────
heading("Funding operating wallets...")
with acting_as(owner):
    def operating_wallet(wallet_type, target_balance, reference):
        wallet = Wallet.objects_unscoped.filter(
            tenant=tenant, owner=owner, wallet_type=wallet_type, account__isnull=False,
        ).first()
        if not wallet:
            wallet = WalletService.create_wallet(
                owner=owner, tenant=tenant, wallet_type=wallet_type,
            )
        if wallet.balance < target_balance:
            WalletService.credit(
                wallet, target_balance - wallet.balance, reference,
                source_account=cash_account,
            )
        return wallet

    personal_wallet = operating_wallet(WalletType.PERSONAL, Decimal("25000.00"), "SEED-PERSONAL")
    business_wallet = operating_wallet(WalletType.BUSINESS, Decimal("150000.00"), "SEED-BUSINESS")
print(f"  Personal : {personal_wallet.balance} ETB")
print(f"  Business : {business_wallet.balance} ETB")


# ── Loan portfolio ────────────────────────────────────────────────────────────
heading("Building the loan portfolio...")


def make_loan(key, product, borrower, principal, term, notes):
    """Create (or fetch) a loan. The idempotency key makes re-runs stable."""
    with acting_as(officer):
        return LoanService.create_loan(
            product=product, borrower=borrower, tenant=tenant,
            principal_amount=principal, term_months=term,
            idempotency_key=f"demo-{key}", notes=notes,
        )


def advance(loan, to_status, approver=None):
    """Walk a loan forward, skipping transitions it has already made.

    Re-runs without --reset land here with loans already part-way through, and
    the state machine rejects a transition it has already performed.
    """
    order = [
        LoanStatus.CREATED, LoanStatus.SUBMITTED, LoanStatus.APPROVED,
        LoanStatus.DISBURSED, LoanStatus.ACTIVE,
    ]
    if loan.status in (LoanStatus.REJECTED, LoanStatus.DEFAULTED, LoanStatus.COMPLETED):
        return loan
    current = order.index(loan.status) if loan.status in order else 0
    target = order.index(to_status)

    if current < 1 <= target:
        with acting_as(officer):
            loan = LoanService.submit_loan(loan)
    if current < 2 <= target:
        with acting_as(approver or finance_manager):
            loan = LoanService.approve_loan(loan, approver=approver or finance_manager)
    if current < 3 <= target:
        with acting_as(finance_manager):
            loan = LoanService.disburse_loan(loan)
    return loan


# 1 — Completed: repaid in full, proves the whole lifecycle closes out.
completed = make_loan("l01", micro, borrowers["almaz"], Decimal("15000.00"), 6,
                      "Shop inventory top-up")
completed = advance(completed, LoanStatus.DISBURSED)
if completed.status != LoanStatus.COMPLETED:
    with acting_as(finance_manager):
        RepaymentSchedule.objects.filter(loan=completed).update(
            status=RepaymentStatus.PAID, paid_at=timezone.now(),
        )
        for inst in RepaymentSchedule.objects.filter(loan=completed):
            inst.amount_paid = inst.total_amount
            inst.save(update_fields=["amount_paid", "updated_at"])
        completed.status = LoanStatus.COMPLETED
        completed.completed_at = timezone.now()
        completed.outstanding_balance = Decimal("0.00")
        completed.save()
print(f"  Completed : {completed.principal_amount} ETB — Almaz Tesfaye")

# 2 — Active and healthy: three installments genuinely repaid through the
#     service, so the ledger and trial balance have real movement behind them.
healthy = make_loan("l02", business, borrowers["dawit"], Decimal("80000.00"), 12,
                    "Bakery equipment financing")
healthy = advance(healthy, LoanStatus.DISBURSED)
with acting_as(finance_manager):
    due = RepaymentSchedule.objects.filter(
        loan=healthy, status=RepaymentStatus.PENDING,
    ).order_by("installment_number")[:3]
    for inst in due:
        RepaymentService.process_repayment(
            healthy, inst.total_amount, idempotency_key=f"demo-l02-r{inst.installment_number}",
        )
healthy.refresh_from_db()
print(f"  Active    : {healthy.principal_amount} ETB — Dawit Bekele (3 repayments)")

# 3 — Active but in arrears: back-dated installments plus a penalty, so the
#     dashboard's overdue metric and the at-risk story are not hypothetical.
arrears = make_loan("l03", agri, borrowers["hanna"], Decimal("45000.00"), 9,
                    "Seasonal fertiliser purchase")
arrears = advance(arrears, LoanStatus.DISBURSED)
with acting_as(finance_manager):
    # Guarded: without it a re-run back-dates the *next* two pending
    # installments each time and the arrears quietly grow with every seed.
    already_overdue = RepaymentSchedule.objects.filter(
        loan=arrears, status=RepaymentStatus.OVERDUE,
    ).exists()
    if not already_overdue:
        stale = RepaymentSchedule.objects.filter(
            loan=arrears, status=RepaymentStatus.PENDING,
        ).order_by("installment_number")[:2]
        for offset, inst in enumerate(stale):
            inst.due_date = (timezone.now() - timedelta(days=45 - offset * 30)).date()
            inst.save(update_fields=["due_date", "updated_at"])
        RepaymentService.check_overdue()
    for inst in RepaymentSchedule.objects.filter(loan=arrears, status=RepaymentStatus.OVERDUE):
        if inst.penalty_amount == Decimal("0.00"):
            RepaymentService.apply_penalty(inst)
overdue_count = RepaymentSchedule.objects.filter(
    loan=arrears, status=RepaymentStatus.OVERDUE,
).count()
print(f"  Arrears   : {arrears.principal_amount} ETB — Hanna Girma ({overdue_count} overdue)")

# 4 — Defaulted: the unhappy ending has to be visible too.
defaulted = make_loan("l04", micro, borrowers["kebede"], Decimal("12000.00"), 6,
                      "Written off after 120 days")
defaulted = advance(defaulted, LoanStatus.DISBURSED)
if defaulted.status not in (LoanStatus.DEFAULTED, LoanStatus.COMPLETED):
    with acting_as(finance_manager):
        defaulted = LoanService.default_loan(defaulted)
print(f"  Defaulted : {defaulted.principal_amount} ETB — Kebede Worku")

# 5 & 6 — Awaiting approval. These are what the approver sees in My Tasks.
pending_small = make_loan("l05", micro, borrowers["yonas"], Decimal("30000.00"), 12,
                          "School fees for two children")
pending_small = advance(pending_small, LoanStatus.SUBMITTED)
print(f"  Submitted : {pending_small.principal_amount} ETB — Yonas Alemu")

pending_large = make_loan("l06", business, borrowers["meron"], Decimal("120000.00"), 18,
                          "Second delivery van")
pending_large = advance(pending_large, LoanStatus.SUBMITTED)
print(f"  Submitted : {pending_large.principal_amount} ETB — Meron Haile")

# 7 — Rejected, so the loan list shows a terminal negative outcome.
rejected = make_loan("l07", agri, borrowers["almaz"], Decimal("8000.00"), 3,
                     "Declined — insufficient repayment history")
rejected = advance(rejected, LoanStatus.SUBMITTED)
if rejected.status == LoanStatus.SUBMITTED:
    with acting_as(analyst):
        rejected = LoanService.reject_loan(rejected)
print(f"  Rejected  : {rejected.principal_amount} ETB — Almaz Tesfaye")

# 8 — Draft, so the "create then submit" path has something to start from.
draft = make_loan("l08", micro, borrowers["dawit"], Decimal("6000.00"), 4,
                  "Draft — awaiting borrower documents")
print(f"  Draft     : {draft.principal_amount} ETB — Dawit Bekele")


# ── Workflow ──────────────────────────────────────────────────────────────────
heading("Creating approval workflow...")
WORKFLOW_CONFIG = {
    "steps": [
        {
            "order": 1,
            "name": "Credit Review",
            "type": "approval",
            "assignee_type": "role",
            "assignee_value": "credit_analyst",
        },
        {
            # Only large loans need a second signature — this is the branch that
            # makes the conditions engine worth showing rather than describing.
            "order": 2,
            "name": "Finance Manager Sign-off",
            "type": "approval",
            "assignee_type": "role",
            "assignee_value": "finance_manager",
            "conditions": [
                {"field": "principal_amount", "operator": "gte", "value": 50000}
            ],
        },
        {
            "order": 3,
            "name": "Notify Borrower",
            "type": "notification",
            "auto_execute": True,
        },
    ]
}

definition = WorkflowDefinition.objects_unscoped.filter(
    tenant=tenant, name="Loan Approval",
).order_by("-version").first()
if definition is None:
    with acting_as(owner):
        definition = WorkflowService.create_definition(
            name="Loan Approval", trigger_event="loan.submitted",
            config=WORKFLOW_CONFIG, tenant=tenant,
        )
    print(f"  Created: {definition.name} v{definition.version}")
else:
    print(f"  Exists : {definition.name} v{definition.version}")

for loan in (pending_small, pending_large):
    # entity_type is matched case-insensitively on purpose: this script writes
    # "loan", handle_loan_submitted writes "Loan", and an exact match here would
    # miss one the event handler had already created and instantiate a second.
    already = WorkflowInstance.objects_unscoped.filter(
        tenant=tenant, entity_type__iexact="loan", entity_id=str(loan.id),
    ).exists()
    if already:
        continue
    with acting_as(officer):
        WorkflowService.instantiate(
            definition=definition, entity_type="loan", entity_id=str(loan.id),
            context={
                "principal_amount": float(loan.principal_amount),
                "term_months": loan.term_months,
                "product": loan.product.name,
                "borrower": f"{loan.borrower.first_name} {loan.borrower.last_name}".strip(),
            },
            tenant=tenant,
        )
waiting = WorkflowStep.objects_unscoped.filter(tenant=tenant, status="in_progress").count()
print(f"  {waiting} step(s) waiting for approval")


# ── Billing ───────────────────────────────────────────────────────────────────
heading("Setting up billing...")
subscription = Subscription.objects_unscoped.filter(tenant=tenant).first()
if subscription is None:
    subscription = Subscription.objects_unscoped.create(
        tenant=tenant, plan=plans["growth"], status=SubscriptionStatus.ACTIVE,
        billing_cycle=BillingCycle.MONTHLY, gateway_provider=GatewayProvider.CHAPA,
        current_period_start=timezone.now() - timedelta(days=6),
        current_period_end=timezone.now() + timedelta(days=24),
    )
    print(f"  Subscribed to {subscription.plan.name}")
else:
    print(f"  Subscribed to {subscription.plan.name} (exists)")

INVOICES = [
    ("INV-DEMO-0001", InvoiceStatus.PAID, 62, True),
    ("INV-DEMO-0002", InvoiceStatus.PAID, 31, True),
    ("INV-DEMO-0003", InvoiceStatus.ISSUED, -24, False),
]
for number, status, days_ago, paid in INVOICES:
    invoice, created = Invoice.objects_unscoped.get_or_create(
        invoice_number=number,
        defaults=dict(
            tenant=tenant, subscription=subscription, status=status,
            amount=Decimal(subscription.plan.monthly_price),
            currency=subscription.plan.currency,
            due_date=(timezone.now() - timedelta(days=days_ago)).date(),
            paid_at=timezone.now() - timedelta(days=days_ago) if paid else None,
        ),
    )
    if created and paid:
        PaymentRecord.objects_unscoped.create(
            tenant=tenant, invoice=invoice, status=PaymentStatus.COMPLETED,
            amount=invoice.amount, currency=invoice.currency,
            gateway_reference=f"chapa-{number.lower()}",
            gateway_provider=GatewayProvider.CHAPA,
            idempotency_key=f"seed-{number.lower()}",
        )
print(f"  {Invoice.objects_unscoped.filter(tenant=tenant).count()} invoices")


# ── Notifications ─────────────────────────────────────────────────────────────
heading("Creating notifications...")

# NotificationService fans out to every enabled channel, and the email channel
# records a Notification row of its own. Left on, the bell would show each alert
# twice and the seed would print an email per notification to stdout. Turning
# email off is also the honest default for a local demo environment.
NOTIFIED_EVENTS = ["loan.submitted", "loan.overdue", "loan.repaid", "workflow.step_assigned"]
for person in [owner, *staff.values()]:
    for event_type in NOTIFIED_EVENTS:
        NotificationPreference.objects_unscoped.get_or_create(
            tenant=tenant, user=person, event_type=event_type,
            defaults={"in_app_enabled": True, "email_enabled": False},
        )

if not Notification.objects_unscoped.filter(tenant=tenant, recipient=owner).exists():
    NotificationService.notify(
        user=owner, tenant=tenant, event_type="loan.submitted",
        title="Loan awaiting your review",
        body=f"Meron Haile submitted a {pending_large.principal_amount} ETB "
             f"application for {pending_large.product.name}.",
        entity_type="loan", entity_id=pending_large.id,
    )
    NotificationService.notify(
        user=owner, tenant=tenant, event_type="loan.overdue",
        title="Installments overdue",
        body=f"Hanna Girma has {overdue_count} overdue installment(s). "
             f"A late-payment penalty has been applied.",
        entity_type="loan", entity_id=arrears.id,
    )
    NotificationService.notify(
        user=owner, tenant=tenant, event_type="loan.repaid",
        title="Repayment received",
        body=f"Dawit Bekele repaid three installments on {healthy.product.name}.",
        entity_type="loan", entity_id=healthy.id,
    )
unread = Notification.objects_unscoped.filter(
    tenant=tenant, recipient=owner,
).exclude(status="read").count()
print(f"  {unread} unread for {EMAIL}")


# ── Settle ────────────────────────────────────────────────────────────────────
# Everything above emitted events that nothing dispatched. Leaving them PENDING
# would hand the next worker that runs recover_pending_events a licence to redo
# the whole seed's fan-out against state it no longer matches.
heading("Settling domain events...")
settle_pending_events(tenant, "raised by this run")


# ── Summary ───────────────────────────────────────────────────────────────────
loan_counts = {}
for loan in Loan.objects_unscoped.filter(tenant=tenant):
    loan_counts[loan.status] = loan_counts.get(loan.status, 0) + 1

print("\n" + "─" * 62)
print("Seed complete.")
print("─" * 62)
print(f"  Tenant       : {tenant.name} ({tenant.slug})")
print(f"  Login        : http://localhost:3000/login")
print(f"  Owner        : {EMAIL}")
print(f"  Team logins  : {', '.join(e for e, *_ in STAFF)}")
print(f"  Password     : {DEMO_PASSWORD} (accounts created by this script)")
print(f"  Loans        : " + ", ".join(f"{n} {s}" for s, n in sorted(loan_counts.items())))
print(f"  Pending tasks: {waiting} awaiting approval in My Tasks")
print(f"  Audit entries: {AuditLog.objects.filter(tenant=tenant).count()}")
if not args.reset:
    print("\n  Re-run with --reset to rebuild this tenant from a clean slate.")
