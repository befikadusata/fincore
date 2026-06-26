from django.db import models


class LoanStatus(models.TextChoices):
    CREATED = 'created', 'Created'
    SUBMITTED = 'submitted', 'Submitted'
    UNDER_REVIEW = 'under_review', 'Under Review'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    DISBURSED = 'disbursed', 'Disbursed'
    ACTIVE = 'active', 'Active'
    COMPLETED = 'completed', 'Completed'
    DEFAULTED = 'defaulted', 'Defaulted'
    RETURNED = 'returned', 'Returned'


class TransactionType(models.TextChoices):
    DISBURSEMENT = 'disbursement', 'Disbursement'
    REPAYMENT = 'repayment', 'Repayment'
    FEE = 'fee', 'Fee'
    PENALTY = 'penalty', 'Penalty'
    ADJUSTMENT = 'adjustment', 'Adjustment'
    TRANSFER = 'transfer', 'Transfer'


class TransactionStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'
    REVERSED = 'reversed', 'Reversed'


class AccountType(models.TextChoices):
    ASSET = 'asset', 'Asset'
    LIABILITY = 'liability', 'Liability'
    EQUITY = 'equity', 'Equity'
    REVENUE = 'revenue', 'Revenue'
    EXPENSE = 'expense', 'Expense'


class AccountCategory(models.TextChoices):
    CASH = 'cash', 'Cash'
    LOAN_RECEIVABLE = 'loan_receivable', 'Loan Receivable'
    INTEREST_RECEIVABLE = 'interest_receivable', 'Interest Receivable'
    FEE_RECEIVABLE = 'fee_receivable', 'Fee Receivable'
    BORROWER_WALLET = 'borrower_wallet', 'Borrower Wallet'
    INTEREST_REVENUE = 'interest_revenue', 'Interest Revenue'
    FEE_REVENUE = 'fee_revenue', 'Fee Revenue'
    PENALTY_REVENUE = 'penalty_revenue', 'Penalty Revenue'


class WalletType(models.TextChoices):
    PERSONAL = 'personal', 'Personal'
    BUSINESS = 'business', 'Business'
    ESCROW = 'escrow', 'Escrow'


class WalletStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    FROZEN = 'frozen', 'Frozen'
    CLOSED = 'closed', 'Closed'


class EntryType(models.TextChoices):
    DEBIT = 'debit', 'Debit'
    CREDIT = 'credit', 'Credit'


class InterestType(models.TextChoices):
    FLAT = 'flat', 'Flat'
    REDUCING_BALANCE = 'reducing_balance', 'Reducing Balance'
    COMPOUND = 'compound', 'Compound'


class RepaymentStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PAID = 'paid', 'Paid'
    PARTIAL = 'partial', 'Partial'
    OVERDUE = 'overdue', 'Overdue'
    WAIVED = 'waived', 'Waived'
