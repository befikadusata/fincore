import logging

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from apps.billing.services.billing_service import BillingService
from apps.billing.services.gateways.chapa import ChapaGateway

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class ChapaWebhookView(View):
    def post(self, request):
        signature = request.META.get('HTTP_CHAPA_SIGNATURE', '')
        payload = request.body
        gateway = ChapaGateway()

        try:
            BillingService.process_webhook(payload, signature, gateway)
            return JsonResponse({'status': 'ok'})
        except ValueError as exc:
            logger.warning('Chapa webhook rejected: %s', exc)
            return JsonResponse({'error': str(exc)}, status=400)
        except Exception as exc:
            logger.error('Chapa webhook error: %s', exc)
            return JsonResponse({'error': 'Internal error'}, status=500)
