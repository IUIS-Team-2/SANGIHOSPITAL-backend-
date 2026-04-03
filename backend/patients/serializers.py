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
        fields = ['id', 'svcName', 'svcCat', 'svcDate', 'svcQty', 'svcRate', 'svcTot']

    def to_internal_value(self, data):
        resource_data = data.copy()

        # 1. Map Name (React sends 'title')
        if 'title' in resource_data and not resource_data.get('svcName'):
            resource_data['svcName'] = resource_data['title']
            
        # 2. Map Category (React sends 'type')
        if 'type' in resource_data and not resource_data.get('svcCat'):
            resource_data['svcCat'] = resource_data['type']

        # 3. Map Rate (React sends 'rate')
        if 'rate' in resource_data and not resource_data.get('svcRate'):
            resource_data['svcRate'] = resource_data['rate']

        # 4. Map Quantity (React sends 'qty')
        if 'qty' in resource_data and not resource_data.get('svcQty'):
            resource_data['svcQty'] = resource_data['qty']

        # 5. AUTO-CALCULATE TOTAL! (Since React forgot to send it)
        if not resource_data.get('svcTot'):
            try:
                rate = float(resource_data.get('svcRate', 0))
                qty = int(resource_data.get('svcQty', 1))
                resource_data['svcTot'] = rate * qty
            except (ValueError, TypeError):
                resource_data['svcTot'] = 0

        return super().to_internal_value(resource_data)
    
    
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

    # 🌟 THE BACKEND SANITIZER
    # This catches empty strings ("") from React and turns them into None (null)
    def to_internal_value(self, data):
        # List of all Date fields that might come in as empty strings
        date_fields = ['dob', 'tpaValidity', 'tpaPanelValidity']
        
        # We create a copy so we don't mutate the original request data unexpectedly
        resource_data = data.copy()
        
        for field in date_fields:
            if resource_data.get(field) == "":
                resource_data[field] = None
                
        return super().to_internal_value(resource_data)

    def validate(self, data):
        # 🌟 Get the ID of the current patient if we are doing an UPDATE
        current_patient_id = self.instance.id if self.instance else None

        # 1. Check for Duplicate Phone Number
        phone = data.get('phone')
        if phone:
            phone_query = Patient.objects.filter(phone=phone)
            if current_patient_id:
                phone_query = phone_query.exclude(id=current_patient_id) # Ignore themselves!
                
            if phone_query.exists():
                raise serializers.ValidationError({"error": f"A patient with phone number {phone} is already registered."})

        # 2. Check for Duplicate National ID (Aadhar/PAN)
        national_id = data.get('nationalId')
        if national_id:
            id_query = Patient.objects.filter(nationalId=national_id)
            if current_patient_id:
                id_query = id_query.exclude(id=current_patient_id) # Ignore themselves!
                
            if id_query.exists():
                raise serializers.ValidationError({"error": f"A patient with National ID {national_id} is already registered."})

        return data