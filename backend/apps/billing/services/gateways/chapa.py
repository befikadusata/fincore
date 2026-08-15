import hashlib
import hmac
import logging
from decimal import Decimal

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from apps.billing.services.gateways.base import PaymentGateway, PaymentInitResult, PaymentVerifyResult

logger = logging.getLogger(__name__)

CHAPA_BASE_URL = 'https://api.chapa.co/v1'
CHAPA_TIMEOUT = 30

# Chapa keys transactions on tx_ref, so replaying an initialize is safe: a retry
# after a dropped connection or a gateway 5xx re-uses the same reference instead
# of opening a second transaction. 4xx and Chapa-level errors are not retried.
_RETRY = Retry(
    total=3,
    connect=3,
    read=3,
    backoff_factor=0.5,  # sleeps 0.5s, 1s, 2s
    status_forcelist=(502, 503, 504),
    allowed_methods=frozenset({'GET', 'POST'}),
)

_SESSION = requests.Session()
_SESSION.mount('https://', HTTPAdapter(max_retries=_RETRY))
_SESSION.mount('http://', HTTPAdapter(max_retries=_RETRY))


class ChapaGateway(PaymentGateway):
    def __init__(self, secret_key: str = '', webhook_secret: str = ''):
        self.secret_key = secret_key or getattr(settings, 'CHAPA_SECRET_KEY', '')
        self.webhook_secret = webhook_secret or getattr(settings, 'CHAPA_WEBHOOK_SECRET', '')

    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json',
        }

    def initialize_payment(
        self,
        amount: Decimal,
        currency: str,
        callback_url: str,
        reference: str,
        customer_email: str,
        customer_name: str = '',
        return_url: str = '',
    ) -> PaymentInitResult:
        name_parts = customer_name.split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        payload = {
            'amount': str(amount),
            'currency': currency,
            'email': customer_email,
            'first_name': first_name,
            'last_name': last_name,
            'tx_ref': reference,
            'callback_url': callback_url,
            'return_url': return_url or callback_url,
        }

        response = _SESSION.post(
            f'{CHAPA_BASE_URL}/transaction/initialize',
            json=payload,
            headers=self._headers(),
            timeout=CHAPA_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        if data.get('status') != 'success':
            raise ValueError(f"Chapa initialization failed: {data.get('message')}")

        return PaymentInitResult(
            checkout_url=data['data']['checkout_url'],
            reference=reference,
        )

    def verify_payment(self, reference: str) -> PaymentVerifyResult:
        response = _SESSION.get(
            f'{CHAPA_BASE_URL}/transaction/verify/{reference}',
            headers=self._headers(),
            timeout=CHAPA_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        if data.get('status') != 'success':
            return PaymentVerifyResult(
                status='failed',
                reference=reference,
                amount=Decimal('0'),
                currency='',
                metadata=data,
            )

        tx_data = data.get('data', {})
        chapa_status = tx_data.get('status', '')
        mapped_status = {
            'success': 'success',
            'failed': 'failed',
            'pending': 'pending',
        }.get(chapa_status.lower(), 'pending')

        return PaymentVerifyResult(
            status=mapped_status,
            reference=reference,
            amount=Decimal(str(tx_data.get('amount', '0'))),
            currency=tx_data.get('currency', ''),
            metadata=tx_data,
        )

    def validate_webhook_signature(self, payload: bytes, signature: str) -> bool:
        if not self.webhook_secret:
            return False
        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
