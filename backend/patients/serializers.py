from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from .models import Patient, Admission, MedicalHistory, Discharge, Service, Billing, ServiceMaster, DischargeSummary
from .models import Task
from .models import LabReport

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

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.admission and instance.admission.dateTime:
            local_dt = timezone.localtime(instance.admission.dateTime)
            data['doa'] = local_dt.strftime('%Y-%m-%dT%H:%M')
        return data

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'svcName', 'svcCat', 'svcDate', 'svcQty', 'svcRate', 'svcTot']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        # Your existing custom mappings for the frontend
        data['title'] = data.get('svcName')
        data['type'] = data.get('svcCat')
        data['rate'] = data.get('svcRate')
        data['qty'] = data.get('svcQty')
        data['total'] = data.get('svcTot')

        request = self.context.get('request')
        if request and getattr(request.user, 'role', '') != 'office_admin':
            if getattr(instance, 'pricing_applied', 'CASH') == 'CASHLESS':
                # Remove the database fields
                data.pop('svcRate', None)
                data.pop('svcTot', None)
                # Remove the custom frontend mapped fields
                data.pop('rate', None)
                data.pop('total', None)
                
        return data

    def to_internal_value(self, data):
        resource_data = data.copy()

        if 'title' in resource_data and not resource_data.get('svcName'):
            resource_data['svcName'] = resource_data['title']
        if 'type' in resource_data and not resource_data.get('svcCat'):
            resource_data['svcCat'] = resource_data['type']
        if 'date' in resource_data and not resource_data.get('svcDate'):
            resource_data['svcDate'] = resource_data['date']

        if resource_data.get('svcDate') == "":
            resource_data['svcDate'] = None
        if not resource_data.get('svcName') or str(resource_data.get('svcName')).strip() == "":
            resource_data['svcName'] = "Service Charge" 

        try:
            raw_rate = resource_data.get('svcRate') or resource_data.get('rate') or 0
            raw_qty = resource_data.get('svcQty') or resource_data.get('qty') or 1
            rate = float(raw_rate)
            qty = int(raw_qty)
            resource_data['svcRate'] = rate
            resource_data['svcQty'] = qty
            resource_data['svcTot'] = rate * qty
        except (ValueError, TypeError):
            resource_data['svcRate'] = 0
            resource_data['svcQty'] = 1
            resource_data['svcTot'] = 0

        return super().to_internal_value(resource_data)
    
    
class BillingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Billing
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')

        if request and getattr(request.user, 'role', '') != 'office_admin':
            if getattr(instance, 'bill_type', 'CASH') == 'CASHLESS':
                data.pop('paymentMode', None)
                data.pop('paidNow', None)
                
        return data
class AdmissionSerializer(serializers.ModelSerializer):
    medicalHistory = MedicalHistorySerializer(read_only=True)
    discharge = DischargeSerializer(read_only=True)
    services = ServiceSerializer(many=True, read_only=True)
    billing = BillingSerializer(read_only=True)

    class Meta:
        model = Admission
        fields = '__all__'
        
    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.dateTime:
            local_dt = timezone.localtime(instance.dateTime)
            data['dateTime'] = local_dt.strftime('%Y-%m-%dT%H:%M')
        return data

class PatientSerializer(serializers.ModelSerializer):
    admissions = AdmissionSerializer(many=True, read_only=True)

    class Meta:
        model = Patient
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        
        if instance.dob:
            from datetime import date
            today = date.today()
            dob = instance.dob
            
            years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
            months = today.month - dob.month
            if today.day < dob.day:
                months -= 1
            if months < 0:
                months += 12

            days = today.day - dob.day
            if days < 0:
                days += 30 
                
            data['ageYY'] = years
            data['ageMM'] = months
            data['ageDD'] = days
            
        return data
    def to_internal_value(self, data):
        date_fields = ['dob', 'tpaValidity', 'tpaPanelValidity']
        resource_data = data.copy()
        
        for field in date_fields:
            if resource_data.get(field) == "":
                resource_data[field] = None
                
        return super().to_internal_value(resource_data)

    def validate(self, data):
        current_patient_id = self.instance.id if self.instance else None
        phone = data.get('phone')
        if phone:
            phone_query = Patient.objects.filter(phone=phone)
            if current_patient_id:
                phone_query = phone_query.exclude(id=current_patient_id)
                
            if phone_query.exists():
                raise serializers.ValidationError({"error": f"A patient with phone number {phone} is already registered."})
            
        national_id = data.get('nationalId')
        if national_id:
            id_query = Patient.objects.filter(nationalId=national_id)
            if current_patient_id:
                id_query = id_query.exclude(id=current_patient_id)
                
            if id_query.exists():
                raise serializers.ValidationError({"error": f"A patient with National ID {national_id} is already registered."})

        return data
    
class DischargeSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = DischargeSummary
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by']

class TaskSerializer(serializers.ModelSerializer):
    assigned_by_name = serializers.CharField(source='assigned_by.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)

    class Meta:
        model = Task
        fields = '__all__'

class LabReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabReport
        fields = '__all__'
        read_only_fields = ['patient', 'admission', 'created_by', 'created_at']