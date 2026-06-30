"""
Run with: docker exec fincore_django python seed_demo.py
Seeds a full demo dataset for me@example.com.
"""
import os
import django
from decimal import Decimal
from datetime import timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.utils import timezone
from apps.saas.models import User, Membership, Role, Permission, RolePermission, Plan, PlanFeature
from apps.saas.services.tenant import TenantService
from apps.finance.models.loan_product import LoanProduct
from apps.finance.models.loan import Loan
from apps.finance.models.repayment_schedule import RepaymentSchedule
from apps.finance.models.wallet import Wallet
from apps.finance.models.account import Account
from apps.finance.constants import (
    InterestType, AccountType, AccountCategory,
    WalletType, LoanStatus, RepaymentStatus,
)
from apps.finance.services.loan_service import LoanService
from apps.finance.services.wallet_service import WalletService
from apps.billing.models.subscription import Subscription
from apps.billing.constants import SubscriptionStatus
from core.middleware.tenant import set_current_tenant

EMAIL = "me@example.com"

# ── User ──────────────────────────────────────────────────────────────────────
print(f"Looking up {EMAIL}...")
user = User.objects.filter(email=EMAIL).first()
if not user:
    raise SystemExit(f"User {EMAIL} not found. Register first at /register.")

# ── Tenant ────────────────────────────────────────────────────────────────────
existing = Membership.objects.filter(user=user).select_related("tenant").first()
if existing:
    tenant = existing.tenant
    print(f"Using existing tenant: {tenant.name} ({tenant.slug})")
else:
    print("Creating tenant 'Demo Lending Co'...")
    tenant = TenantService.create_tenant(
        name="Demo Lending Co",
        slug="demo-lending-co",
        owner_user=user,
    )
    print(f"  Created: {tenant.id}")

set_current_tenant(tenant)

# ── Permissions ───────────────────────────────────────────────────────────────
print("Seeding permissions...")
from django.core.management import call_command
call_command("seed_permissions", verbosity=0)

membership = Membership.objects.get(user=user, tenant=tenant)
owner_role, _ = Role.objects.get_or_create(
    tenant=tenant, slug="owner", defaults={"name": "Owner"}
)
RolePermission.objects.bulk_create(
    [RolePermission(role=owner_role, permission=p) for p in Permission.objects.all()],
    ignore_conflicts=True,
)
owner_role.membership.add(membership)
print(f"  {Permission.objects.count()} permissions assigned to Owner role")

# ── Chart of Accounts ─────────────────────────────────────────────────────────
print("Creating chart of accounts...")
accounts_def = [
    ("Cash & Bank",         AccountType.ASSET,     AccountCategory.CASH,               "1000"),
    ("Loan Receivable",     AccountType.ASSET,     AccountCategory.LOAN_RECEIVABLE,    "1100"),
    ("Interest Receivable", AccountType.ASSET,     AccountCategory.INTEREST_RECEIVABLE,"1200"),
    ("Fee Receivable",      AccountType.ASSET,     AccountCategory.FEE_RECEIVABLE,     "1300"),
    ("Borrower Wallet",     AccountType.LIABILITY, AccountCategory.BORROWER_WALLET,    "2000"),
    ("Interest Revenue",    AccountType.REVENUE,   AccountCategory.INTEREST_REVENUE,   "4000"),
    ("Fee Revenue",         AccountType.REVENUE,   AccountCategory.FEE_REVENUE,        "4100"),
    ("Penalty Revenue",     AccountType.REVENUE,   AccountCategory.PENALTY_REVENUE,    "4200"),
]
for name, acct_type, category, code in accounts_def:
    Account.objects.get_or_create(
        tenant=tenant, category=category,
        defaults={"name": name, "account_type": acct_type, "code": code},
    )
print(f"  {len(accounts_def)} accounts ready")

# ── Loan Products ─────────────────────────────────────────────────────────────
print("Creating loan products...")
products_def = [
    dict(
        name="Personal Micro Loan",
        description="Short-term personal loan for small needs",
        interest_type=InterestType.FLAT,
        interest_rate=Decimal("15.00"),
        min_term_months=1, max_term_months=12,
        min_amount=Decimal("1000.00"), max_amount=Decimal("50000.00"),
        fees_config={"origination_fee_pct": 1.5},
    ),
    dict(
        name="Business Growth Loan",
        description="Medium-term loan for business expansion",
        interest_type=InterestType.REDUCING_BALANCE,
        interest_rate=Decimal("18.00"),
        min_term_months=3, max_term_months=24,
        min_amount=Decimal("10000.00"), max_amount=Decimal("500000.00"),
        fees_config={"origination_fee_pct": 2.0, "insurance_fee_pct": 0.5},
    ),
    dict(
        name="Agriculture Seasonal Loan",
        description="Seasonal financing for farmers",
        interest_type=InterestType.FLAT,
        interest_rate=Decimal("12.00"),
        min_term_months=3, max_term_months=9,
        min_amount=Decimal("5000.00"), max_amount=Decimal("200000.00"),
        fees_config={},
    ),
]
products = []
for p in products_def:
    obj, created = LoanProduct.objects.get_or_create(
        tenant=tenant, name=p["name"], defaults=p
    )
    products.append(obj)
    print(f"  {'Created' if created else 'Exists '}: {obj.name}")

micro_product, business_product, agri_product = products

# ── Wallets ───────────────────────────────────────────────────────────────────
# Pre-create both wallets with proper accounts so disburse_loan reuses them.
print("Creating wallets...")
cash_account = Account.objects_unscoped.get(tenant=tenant, code="1000")

def get_or_create_wallet(wallet_type):
    """Get existing wallet (with account) or create via WalletService."""
    w = Wallet.objects_unscoped.filter(
        tenant=tenant, owner=user, wallet_type=wallet_type, account__isnull=False
    ).first()
    if not w:
        w = WalletService.create_wallet(owner=user, tenant=tenant, wallet_type=wallet_type)
    return w

personal_wallet = get_or_create_wallet(WalletType.PERSONAL)
business_wallet = get_or_create_wallet(WalletType.BUSINESS)

if personal_wallet.balance < Decimal("25000.00"):
    top_up = Decimal("25000.00") - personal_wallet.balance
    WalletService.credit(personal_wallet, top_up, "SEED-PERSONAL-INIT", source_account=cash_account)
    print(f"  Personal wallet: 25,000 ETB")
else:
    print(f"  Personal wallet: {personal_wallet.balance} ETB (exists)")

if business_wallet.balance < Decimal("150000.00"):
    top_up = Decimal("150000.00") - business_wallet.balance
    WalletService.credit(business_wallet, top_up, "SEED-BIZ-INIT", source_account=cash_account)
    print(f"  Business wallet: 150,000 ETB")
else:
    print(f"  Business wallet: {business_wallet.balance} ETB (exists)")

# ── Loans ─────────────────────────────────────────────────────────────────────
print("Creating demo loans...")

def make_loan(product, principal, term, notes, status_steps):
    """Create a loan and advance it through the given status steps."""
    existing = Loan.objects_unscoped.filter(
        tenant=tenant, product=product, principal_amount=principal, notes=notes
    ).first()
    if existing:
        print(f"  Exists : {notes} ({existing.status})")
        return existing
    loan = LoanService.create_loan(
        product=product, borrower=user, tenant=tenant,
        principal_amount=principal, term_months=term, notes=notes,
    )
    for step in status_steps:
        step(loan)
    return loan

# 1. Completed loan
def complete_loan(loan):
    LoanService.submit_loan(loan)
    LoanService.approve_loan(loan, approver=user)
    LoanService.disburse_loan(loan)
    RepaymentSchedule.objects.filter(loan=loan).update(
        status=RepaymentStatus.PAID,
        amount_paid=loan.total_amount,
        paid_at=timezone.now(),
    )
    loan.status = LoanStatus.COMPLETED
    loan.completed_at = timezone.now()
    loan.outstanding_balance = Decimal("0.00")
    loan.save()
    print(f"  Created: Completed micro loan {loan.id}")

loan_done = make_loan(
    micro_product, Decimal("15000.00"), 6,
    "Demo completed loan", [complete_loan],
)

# 2. Active loan (disbursed, first 3 installments paid)
def activate_loan(loan):
    LoanService.submit_loan(loan)
    LoanService.approve_loan(loan, approver=user)
    LoanService.disburse_loan(loan)
    for inst in RepaymentSchedule.objects.filter(loan=loan).order_by("installment_number")[:3]:
        inst.status = RepaymentStatus.PAID
        inst.amount_paid = inst.total_amount
        inst.paid_at = timezone.now()
        inst.save()
    print(f"  Created: Active business loan {loan.id} (3 installments paid)")

loan_active = make_loan(
    business_product, Decimal("80000.00"), 12,
    "Demo active business loan", [activate_loan],
)

# 3. Submitted loan (awaiting approval)
def submit_only(loan):
    LoanService.submit_loan(loan)
    print(f"  Created: Submitted loan {loan.id}")

loan_submitted = make_loan(
    micro_product, Decimal("30000.00"), 12,
    "Demo submitted loan", [submit_only],
)

# 4. Draft loan
loan_draft = make_loan(
    agri_product, Decimal("10000.00"), 6,
    "Demo draft loan", [],
)
if loan_draft.status == LoanStatus.CREATED:
    print(f"  Created: Draft loan {loan_draft.id}")


# ── Billing Plans ─────────────────────────────────────────────────────────────
print("Creating billing plans...")
plans_def = [
    dict(
        name="Starter", slug="starter", monthly_price=0, annual_price=0,
        description="Up to 3 members, 50 loans/month",
        features=[
            ("Loan lifecycle", "loan_lifecycle"),
            ("Basic reporting", "basic_reporting"),
        ],
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
starter_plan = None
for p in plans_def:
    features = p.pop("features")
    # Plans are global (unscoped) — use a system-level tenant or null tenant trick
    # The PlanViewSet uses objects_unscoped; create with a dummy tenant lookup
    plan = Plan.objects_unscoped.filter(slug=p["slug"]).first()
    if not plan:
        plan = Plan.objects_unscoped.create(tenant=tenant, **p)
        for fname, fcode in features:
            PlanFeature.objects.get_or_create(
                plan=plan, codename=fcode, defaults={"name": fname}
            )
        print(f"  Created: {plan.name} plan")
    else:
        print(f"  Exists : {plan.name} plan")
    if plan.slug == "starter":
        starter_plan = plan

# Subscribe tenant to Starter if no subscription exists
if starter_plan and not Subscription.objects.filter(tenant=tenant).exists():
    Subscription.objects.create(
        tenant=tenant,
        plan=starter_plan,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )
    print("  Subscribed to Starter plan")

print("\nSeed complete.")
print(f"  Tenant : Demo Lending Co")
print(f"  Login  : http://localhost:3001/login  →  {EMAIL}")
print(f"  Loans  : 1 completed, 1 active, 1 submitted, 1 draft")
print(f"  Wallets: personal (25,000 ETB) + business (150,000 ETB)")
print(f"  Plans  : Starter / Growth / Enterprise")
