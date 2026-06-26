# FinCore — Agent Rules

## Project Context
Multi-tenant fintech SaaS. Django modular monolith, DDD, event-driven.
- **Architecture**: `docs/fincore_architecture.md`
- **Plan**: `docs/fincore_implementation_plan.md`
- Read these BEFORE making architectural decisions. They are the source of truth.

## Stack
Django 5.x · DRF · PostgreSQL 16 · Redis 7 (Streams) · Celery 5 · simplejwt · pytest + factory_boy

## Project Structure
```
fincore/
├── config/settings/{base,development,production,testing}.py
├── core/          # Shared kernel: BaseModel, TenantScopedModel, middleware, utils
├── apps/
│   ├── saas/      # Tenant, User, Membership, Role, Permission
│   ├── finance/   # Loan, Wallet, Account, Transaction, LedgerEntry
│   ├── workflow/  # WorkflowDefinition, Instance, Step
│   ├── audit/     # AuditLog (append-only)
│   ├── events/    # DomainEvent, EventSubscription, Redis Streams
│   ├── notifications/
│   └── billing/   # Subscription, Invoice, Chapa gateway
├── docker/
└── requirements/{base,development,production,testing}.txt
```

## Critical Rules

### Architecture
- Every tenant-scoped model inherits `TenantScopedModel` (abstract, has `tenant` FK)
- Use `TenantManager` for auto-scoped queries. Never manually filter by tenant in business logic.
- All IDs are UUIDs
- Currency stored as integer minor units (santim/cents). No floats for money. Ever.
- Double-entry bookkeeping: every Transaction creates 2+ LedgerEntry records. Debits == Credits.

### Code Patterns
- **Service layer**: Business logic in `services/`, not in views or serializers
- **State machines**: Loan status transitions enforced via `LoanStateMachine`. No ad-hoc status changes.
- **Strategy pattern**: Interest calculators, payment gateways, notification channels
- **Events**: Side effects via event bus, not direct cross-module calls
- **Idempotency**: Financial write ops require `Idempotency-Key` header
- **Audit**: Mutating service methods decorated with `@auditable`

### Testing
- pytest only (no unittest). Use factory_boy for fixtures.
- Test tenant isolation: cross-tenant queries must return empty
- Test double-entry invariant: sum(debits) == sum(credits) per transaction
- Test state machine: invalid transitions must raise

### Style
- Python 3.12+. Type hints on all public functions.
- Docstrings on services and complex logic. Skip obvious ones.
- Keep modules focused. One model per file in `models/` dirs.
- Import apps by label: `from apps.finance.models import Loan`

### API
- All endpoints under `/api/v1/`
- DRF ViewSets + Routers. Permission classes per view.
- Cursor-based pagination for large datasets
- Consistent error format via custom exception handler

### What NOT To Do
- Don't bypass TenantManager with `.objects.all()` on scoped models
- Don't store money as Decimal/float
- Don't put business logic in views or serializers
- Don't make direct cross-module DB queries — use services or events
- Don't create migrations without reviewing them first
- Don't skip idempotency on financial endpoints
