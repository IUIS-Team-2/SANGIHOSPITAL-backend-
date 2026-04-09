from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'branch', 'is_staff']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Hospital Assignment', {'fields': ('role', 'branch')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Hospital Assignment', {'fields': ('role', 'branch')}),
    )

admin.site.register(CustomUser, CustomUserAdmin)