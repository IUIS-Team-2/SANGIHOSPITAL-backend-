from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import datetime

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('superadmin', 'Super Admin'),
        ('admin', 'Branch Admin'),
        ('receptionist', 'Receptionist'),
        ('billing', 'Billing Staff'),
    )

    BRANCH_CHOICES = (
        ('LNM', 'Laxmi Nagar'),
        ('RYM', 'Raya'),
        ('ALL', 'All Branches'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='receptionist')
    branch = models.CharField(max_length=10, choices=BRANCH_CHOICES, null=True, blank=True)
    emp_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
    
class PasswordResetOTP(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        expiration_time = self.created_at + datetime.timedelta(minutes=10)
        return timezone.now() <= expiration_time and not self.is_used

    def __str__(self):
        return f"{self.user.username} - {self.otp}"