from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class PaymentInitResult:
    checkout_url: str
    reference: str


@dataclass
class PaymentVerifyResult:
    status: str  # 'success' | 'failed' | 'pending'
    reference: str
    amount: Decimal
    currency: str
    metadata: dict = field(default_factory=dict)


class PaymentGateway(ABC):
    @abstractmethod
    def initialize_payment(
        self,
        amount: Decimal,
        currency: str,
        callback_url: str,
        reference: str,
        customer_email: str,
        customer_name: str = '',
        return_url: str = '',
    ) -> PaymentInitResult: ...

    @abstractmethod
    def verify_payment(self, reference: str) -> PaymentVerifyResult: ...

    @abstractmethod
    def validate_webhook_signature(self, payload: bytes, signature: str) -> bool: ...
