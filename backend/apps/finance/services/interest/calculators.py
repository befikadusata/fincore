from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol, runtime_checkable

from apps.finance.constants import InterestType


@dataclass(frozen=True)
class InterestResult:
    total_interest: Decimal
    total_repayable: Decimal
    monthly_payment: Decimal


@runtime_checkable
class InterestCalculator(Protocol):
    def calculate(self, principal: Decimal, annual_rate: Decimal, term_months: int) -> InterestResult:
        ...


class FlatInterestCalculator:
    """
    Interest is computed on the original principal for the full term.
    total_interest = principal × (annual_rate / 100) × (term_months / 12)
    Each monthly payment = total_repayable / term_months
    """

    def calculate(self, principal: Decimal, annual_rate: Decimal, term_months: int) -> InterestResult:
        if term_months <= 0:
            raise ValueError("term_months must be positive")
        if principal <= 0:
            raise ValueError("principal must be positive")
        if annual_rate < 0:
            raise ValueError("annual_rate cannot be negative")

        total_interest = (principal * (annual_rate / Decimal('100')) * Decimal(term_months) / Decimal('12')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        total_repayable = principal + total_interest
        monthly_payment = (total_repayable / Decimal(term_months)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        return InterestResult(
            total_interest=total_interest,
            total_repayable=total_repayable,
            monthly_payment=monthly_payment,
        )


class ReducingBalanceCalculator:
    """
    Standard amortising loan (equal monthly payments on declining balance).
    Uses the annuity formula: PMT = P × r(1+r)^n / ((1+r)^n − 1)
    where r = annual_rate / (100 × 12), n = term_months.
    Zero-rate edge case: PMT = P / n.
    """

    def calculate(self, principal: Decimal, annual_rate: Decimal, term_months: int) -> InterestResult:
        if term_months <= 0:
            raise ValueError("term_months must be positive")
        if principal <= 0:
            raise ValueError("principal must be positive")
        if annual_rate < 0:
            raise ValueError("annual_rate cannot be negative")

        r = annual_rate / Decimal('1200')  # monthly rate as decimal

        if r == 0:
            monthly_payment = (principal / Decimal(term_months)).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        else:
            n = Decimal(term_months)
            factor = (1 + r) ** int(term_months)
            monthly_payment = (principal * r * factor / (factor - 1)).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )

        total_repayable = (monthly_payment * term_months).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        total_interest = total_repayable - principal

        return InterestResult(
            total_interest=total_interest,
            total_repayable=total_repayable,
            monthly_payment=monthly_payment,
        )


class InterestCalculatorFactory:
    _registry: dict[str, type] = {
        InterestType.FLAT: FlatInterestCalculator,
        InterestType.REDUCING_BALANCE: ReducingBalanceCalculator,
    }

    @classmethod
    def for_product(cls, product) -> InterestCalculator:
        """Returns the appropriate calculator instance for a LoanProduct."""
        calculator_class = cls._registry.get(product.interest_type)
        if calculator_class is None:
            raise NotImplementedError(
                f"No interest calculator registered for type '{product.interest_type}'"
            )
        return calculator_class()

    @classmethod
    def get(cls, interest_type: str) -> InterestCalculator:
        """Returns a calculator instance by interest_type string."""
        calculator_class = cls._registry.get(interest_type)
        if calculator_class is None:
            raise NotImplementedError(
                f"No interest calculator registered for type '{interest_type}'"
            )
        return calculator_class()
