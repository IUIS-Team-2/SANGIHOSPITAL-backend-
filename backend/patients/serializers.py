from rest_framework import serializers
from django.db import transaction
# 🌟 Make sure ServiceMaster is imported here!
from .models import Patient, Admission, MedicalHistory, Discharge, Service, Billing, ServiceMaster

class ServiceMasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceMaster
        fields = '__all__'

class MedicalHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalHistory
        fields = '__all__'

class DischargeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discharge
        fields = '__all__'

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'
        read_only_fields = ['admission']

class BillingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Billing
        fields = '__all__'

class AdmissionSerializer(serializers.ModelSerializer):
    medicalHistory = MedicalHistorySerializer(read_only=True)
    discharge = DischargeSerializer(read_only=True)
    services = ServiceSerializer(many=True, read_only=True)
    billing = BillingSerializer(read_only=True)

    class Meta:
        model = Admission
        fields = '__all__'

class PatientSerializer(serializers.ModelSerializer):
    admissions = AdmissionSerializer(many=True, read_only=True)

    class Meta:
        model = Patient
        fields = '__all__'

    # 🌟 NEW: Duplicate Check Logic
    def validate(self, data):
        phone = data.get('phone')
        national_id = data.get('nationalId')

        # Check if a patient with this phone number already exists
        if phone and Patient.objects.filter(phone=phone).exists():
            raise serializers.ValidationError({"error": f"A patient with phone number {phone} is already registered."})
        
        # Check if a patient with this National ID already exists
        if national_id and Patient.objects.filter(nationalId=national_id).exists():
            raise serializers.ValidationError({"error": f"A patient with National ID {national_id} is already registered."})
            
        return data

    def create(self, validated_data):
        with transaction.atomic():
            patient = Patient.objects.create(**validated_data)

            admission = Admission.objects.create(
                patient=patient,
                admNo=1  
            )

            MedicalHistory.objects.create(admission=admission)
            Discharge.objects.create(admission=admission)
            Billing.objects.create(admission=admission)

            return patient