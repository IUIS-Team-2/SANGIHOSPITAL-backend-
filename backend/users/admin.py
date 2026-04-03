from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import HospitalUser

@admin.register(HospitalUser)
class HospitalUserAdmin(UserAdmin):
    model = HospitalUser
    list_display = ['username', 'email', 'branch', 'is_staff']
    fieldsets = UserAdmin.fieldsets + (
        ('Hospital Info', {'fields': ('branch', 'phone_number')}),
    )