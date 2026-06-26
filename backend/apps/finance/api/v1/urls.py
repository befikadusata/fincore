from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.finance.api.v1.views import (
    LoanProductViewSet,
    LoanViewSet,
    TrialBalanceView,
    WalletViewSet,
)

router = DefaultRouter()
router.register('loan-products', LoanProductViewSet, basename='loan-product')
router.register('loans', LoanViewSet, basename='loan')
router.register('wallets', WalletViewSet, basename='wallet')

app_name = 'finance'

urlpatterns = [
    path('ledger/trial-balance/', TrialBalanceView.as_view(), name='trial-balance'),
    path('', include(router.urls)),
]
