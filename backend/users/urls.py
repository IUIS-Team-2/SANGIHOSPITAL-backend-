from django.urls import path
from .views import CustomLoginView, UserListCreateView, UserDetailView, AdminResetPasswordView, RequestPasswordResetOTPView, VerifyPasswordResetOTPView
from .views import AdminResetPasswordView

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='api_login'),
    path('manage/', UserListCreateView.as_view(), name='manage_users'),
    path('manage/<int:pk>/', UserDetailView.as_view(), name='manage_user_detail'),
    path('manage/<int:pk>/reset-password/', AdminResetPasswordView.as_view(), name='admin_reset_password'),
    path('request-reset-otp/', RequestPasswordResetOTPView.as_view(), name='request_otp'),
    path('verify-reset-otp/', VerifyPasswordResetOTPView.as_view(), name='verify_otp'), 
]