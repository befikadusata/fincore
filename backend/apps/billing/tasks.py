import logging
from config.celery import app

logger = logging.getLogger(__name__)


@app.task(name='billing.check_subscription_status')
def check_subscription_status():
    from apps.billing.services.billing_service import BillingService
    result = BillingService.check_subscription_status()
    logger.info('Subscription status check complete: %s', result)
    return result
