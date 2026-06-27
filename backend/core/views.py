from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from core.throttles import AuthAnonThrottle, AuthUserThrottle


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_classes = [AuthAnonThrottle]


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = [AuthAnonThrottle]
