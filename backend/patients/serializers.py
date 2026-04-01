from rest_framework import serializers
from .models import Patient, Admission, MedicalHistory, Discharge, Service, Billing
from django.db import transaction

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
    # These match the 'related_name' in our models.py!
    medicalHistory = MedicalHistorySerializer(read_only=True)
    discharge = DischargeSerializer(read_only=True)
    services = ServiceSerializer(many=True, read_only=True)
    billing = BillingSerializer(read_only=True)

    class Meta:
        model = Admission
        fields = '__all__'

class PatientSerializer(serializers.ModelSerializer):
    # This grabs all admissions linked to this patient and nests them inside an 'admissions' array!
    admissions = AdmissionSerializer(many=True, read_only=True)

    class Meta:
        model = Patient
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

    # 🌟 THE NEW SMART LOGIC 🌟
    def create(self, validated_data):
        # We use a 'transaction' so if the admission fails, the patient isn't created either.
        # It's all or nothing—crucial for hospital data integrity!
        with transaction.atomic():
            # 1. Create the Patient
            patient = Patient.objects.create(**validated_data)

            # 2. Automatically create the first Admission (Adm #1)
            # In Sangi Hospital, every new registration is an automatic admission.
            admission = Admission.objects.create(
                patient=patient,
                admNo=1  # First time registration is always Admission #1
            )

            # 3. Create the placeholder records so the frontend doesn't crash 
            # when looking for 'medicalHistory' or 'billing'
            MedicalHistory.objects.create(admission=admission)
            Discharge.objects.create(admission=admission)
            Billing.objects.create(admission=admission)

            return patient