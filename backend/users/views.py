from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import CustomTokenObtainPairSerializer
from rest_framework import generics
from .models import CustomUser
from .serializers import UserManagementSerializer
from .permissions import IsBranchAdminOrSuperAdmin
from rest_framework.response import Response
from rest_framework import status
from .serializers import AdminPasswordResetSerializer, VerifyOTPandResetSerializer
import random
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from .models import PasswordResetOTP
from .serializers import RequestOTPSerializer

class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class UserListCreateView(generics.ListCreateAPIView):
    serializer_class = UserManagementSerializer
    permission_classes = [IsBranchAdminOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'superadmin':
            return CustomUser.objects.all()
        elif user.role == 'admin':
            return CustomUser.objects.filter(branch=user.branch)
        return CustomUser.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == 'admin':
            serializer.save(branch=user.branch)
        else:
            serializer.save()
class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserManagementSerializer
    permission_classes = [IsBranchAdminOrSuperAdmin]

    def get_queryset(self):
        user = self.request.user
        # Super Admin can edit/delete ANY user
        if user.role == 'superadmin':
            return CustomUser.objects.all()
        # Branch Admin can only edit/delete users IN THEIR OWN BRANCH
        elif user.role == 'admin':
            return CustomUser.objects.filter(branch=user.branch)
        return CustomUser.objects.none()
class AdminResetPasswordView(generics.UpdateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = AdminPasswordResetSerializer
    permission_classes = [IsBranchAdminOrSuperAdmin]

    def update(self, request, *args, **kwargs):
        user_to_reset = self.get_object()
        
        # Security: Branch Admin can only reset passwords for their OWN branch
        if request.user.role == 'admin' and user_to_reset.branch != request.user.branch:
            return Response({"error": "You cannot reset passwords for other branches."}, 
                            status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        

        user_to_reset.set_password(serializer.validated_data['new_password'])
        user_to_reset.save()
        
        return Response({"message": f"Password for {user_to_reset.username} reset successfully."}, 
                        status=status.HTTP_200_OK)
    
class RequestPasswordResetOTPView(APIView):
    permission_classes = [AllowAny] 

    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response(
                {"message": "If an account with that email exists, an OTP has been sent."}, 
                status=status.HTTP_200_OK
            )

        # 1. Generate a random 6-digit OTP
        otp_code = str(random.randint(100000, 999999))

        # 2. Invalidate any old unused OTPs for this user so they don't get confused
        PasswordResetOTP.objects.filter(user=user, is_used=False).update(is_used=True)

        # 3. Save the new OTP to the database
        PasswordResetOTP.objects.create(user=user, otp=otp_code)                    

        # 4. Send the Email via Gmail
        subject = "Sangi Hospital - Password Reset OTP"
        message = f"Hello {user.first_name or user.username},\n\nYour password reset code is: {otp_code}\n\nThis code will expire in 10 minutes. If you did not request this, please ignore this email."
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            return Response(
                {"error": "Failed to send email. Check your Gmail configuration."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {"message": "If an account with that email exists, an OTP has been sent."}, 
            status=status.HTTP_200_OK
        )
    
class VerifyPasswordResetOTPView(APIView):
    permission_classes = [AllowAny] # No token required because they forgot their password!

    def post(self, request):
        serializer = VerifyOTPandResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']

        # 1. Find the user
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"error": "Invalid request."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Find the active OTP for this user
        try:
            otp_record = PasswordResetOTP.objects.get(user=user, otp=otp_code, is_used=False)
        except PasswordResetOTP.DoesNotExist:
            return Response({"error": "Invalid or already used OTP."}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Check if the 10-minute timer expired
        if not otp_record.is_valid():
            return Response({"error": "OTP has expired. Please request a new one."}, status=status.HTTP_400_BAD_REQUEST)

        # 4. Success! Change the password and burn the OTP so it can't be reused
        user.set_password(new_password)
        user.save()

        otp_record.is_used = True
        otp_record.save()

        return Response(
            {"message": "Password successfully reset. You can now log in with your new password."}, 
            status=status.HTTP_200_OK
        )