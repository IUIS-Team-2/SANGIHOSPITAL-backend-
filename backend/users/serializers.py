# users/serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import re
from rest_framework import serializers
from .models import CustomUser

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims to the token itself if needed later
        token['role'] = user.role
        token['branch'] = user.branch
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['role'] = self.user.role
        data['branch'] = self.user.branch
        data['username'] = self.user.username
        data['name'] = f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username
        return data
    
class UserManagementSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'role', 'branch', 'emp_id', 'phone_number', 
            'password', 'confirm_password', 'is_active'
        ]

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        if ' ' in value:
            raise serializers.ValidationError("Password cannot contain spaces.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError("Password must contain at least one special character.")
        return value

    def validate(self, data):
        if data.get('password') != data.get('confirm_password'):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = CustomUser.objects.create_user(**validated_data)
        return user
    
class AdminPasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, required=True)
    confirm_new_password = serializers.CharField(write_only=True, required=True)

    def validate_new_password(self, value):
        # We reuse our rules: 8 chars, no spaces, special char
        if len(value) < 8 or ' ' in value or not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError("Password does not meet security requirements.")
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_new_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

class RequestOTPSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class VerifyOTPandResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(max_length=6, required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    confirm_new_password = serializers.CharField(write_only=True, required=True)

    def validate_new_password(self, value):
        # Enforce our strict password rules
        if len(value) < 8 or ' ' in value or not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise serializers.ValidationError("Password must be 8+ chars, no spaces, and have a special character.")
        return value

    def validate(self, data):
        if data.get('new_password') != data.get('confirm_new_password'):
            raise serializers.ValidationError({"confirm_new_password": "Passwords do not match."})
        return data