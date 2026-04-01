# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    BRANCH_CHOICES = [
        ('LNM', 'Laxmi Nagar'),
        ('RYM', 'Raya'),
        ('ALL', 'Super Admin'),
    ]
    branch = models.CharField(max_length=3, choices=BRANCH_CHOICES, default='LNM')
    phone_number = models.CharField(max_length=15, blank=True)

    def __str__(self):
        return f"{self.username} ({self.get_branch_display()})"