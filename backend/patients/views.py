import datetime
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction  
from .models import (
    Patient, 
    Admission, 
    MedicalHistory, 
    Discharge, 
    Service, 
    Billing, 
    ServiceMaster
)
from .serializers import (
    PatientSerializer, 
    MedicalHistorySerializer, 
    DischargeSerializer, 
    ServiceSerializer, 
    BillingSerializer,
    ServiceMasterSerializer
)

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all().order_by('-created_at')
    serializer_class = PatientSerializer
    lookup_field = 'uhid'
    
    # 🌟 THE SECRET SAUCE: This tells Django that UHIDs can contain dashes!
    lookup_value_regex = '[^/]+' 

    # ==========================================
    # 🌟 THE BACKEND FIX: Auto-Create Admission
    # ==========================================
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        patient = serializer.instance 

        try:
            # 🌟 Let models.py handle the IPD Number auto-generation!
            Admission.objects.create(
                patient=patient, 
                admNo=1
            )
            
            response_serializer = self.get_serializer(patient)
            headers = self.get_success_headers(response_serializer.data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        except Exception as e:
            print("🚨 AUTO-ADMISSION FAILED:", str(e))
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'])
    def update_medical(self, request, uhid=None):
        patient = self.get_object()
        adm_no = request.data.get('admNo')
        medical_data = request.data.get('medicalData', {})
        
        try:
            # 🌟 Grab the ACTUAL OBJECT from the database
            admission_obj = patient.admissions.get(admNo=adm_no)
            
            # 🌟 Pass the OBJECT, not the number!
            if not hasattr(admission_obj, 'medicalHistory'):
                MedicalHistory.objects.create(admission=admission_obj)
                
            for key, value in medical_data.items():
                setattr(admission_obj.medicalHistory, key, value)
                
            admission_obj.medicalHistory.save()
            return Response({'status': 'Medical history updated successfully'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'])
    def discharge(self, request, uhid=None):
        patient = self.get_object()
        adm_no = request.data.get('admNo')
        discharge_data = request.data.get('dischargeData', {})
        
        try:
            admission_obj = patient.admissions.get(admNo=adm_no)
            
            if not hasattr(admission_obj, 'discharge'):
                Discharge.objects.create(admission=admission_obj)
                
            for key, value in discharge_data.items():
                # 🌟 THE FIX: Ignore relational keys sent by React!
                if key in ['id', 'admission']:
                    continue
                    
                if key in ['dod', 'expectedDod', 'actualDod'] and value == "":
                    value = None
                setattr(admission_obj.discharge, key, value)
                
            admission_obj.discharge.save()
            return Response({'status': 'Discharge updated successfully'})
            
        except Exception as e:
            print(f"🚨 DISCHARGE ERROR: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=True, methods=['patch'])
    def update_billing(self, request, uhid=None):
        patient = self.get_object()
        adm_no = request.data.get('admNo')
        billing_data = request.data.get('billingData', {})
        
        try:
            admission_obj = patient.admissions.get(admNo=adm_no)
            
            if not hasattr(admission_obj, 'billing'):
                Billing.objects.create(admission=admission_obj)
                
            for key, value in billing_data.items():
                if key in ['id', 'admission']:
                    continue
                    
                # 🌟 THE FIX: The Boolean Sanitizer
                # If React sends an empty string for the checkbox, force it to Python False!
                if key == 'paidNow' and value == "":
                    value = False
                # Just in case React sends string "true"/"false" instead of boolean True/False
                elif key == 'paidNow' and isinstance(value, str):
                    value = value.lower() == "true"
                    
                setattr(admission_obj.billing, key, value)
                
            admission_obj.billing.save()
            return Response({'status': 'Billing updated successfully'})
            
        except Exception as e:
            print(f"🚨 BILLING ERROR: {str(e)}") 
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=True, methods=['post'])
    def add_service(self, request, uhid=None):
        patient = self.get_object()
        adm_no = request.data.get('admNo')
        service_data = request.data.get('serviceData')
        try:
            admission = patient.admissions.get(admNo=adm_no)
            ser = ServiceSerializer(data=service_data)
            if ser.is_valid():
                ser.save(admission=admission)
                return Response({'status': 'Service added', 'data': ser.data})
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=404)
        
    @action(detail=True, methods=['post'])
    def new_admission(self, request, uhid=None): 
        try:
            patient = self.get_object()
            
            last_adm = Admission.objects.filter(patient=patient).order_by('id').last()
            new_adm_no = (last_adm.admNo + 1) if last_adm else 1
            
            
            admission = Admission.objects.create(
                patient=patient, 
                admNo=new_adm_no
            )
            
            return Response({
                "message": "Admission created successfully", 
                "ipdNo": admission.ipdNo 
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            print("🚨 ADMISSION CREATION FAILED:", str(e))
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(detail=True, methods=['patch'])
    def set_expected_dod(self, request, uhid=None):
        patient = self.get_object()
        adm_no = request.data.get('admNo')
        expected_date = request.data.get('expectedDod')
        
        if expected_date == "":
            expected_date = None
        elif expected_date and len(expected_date) > 10:
            expected_date = expected_date[:10]

        try:
            admission = patient.admissions.get(admNo=adm_no)
            if not hasattr(admission, 'discharge'):
                Discharge.objects.create(admission=admission)
            
            admission.discharge.expectedDod = expected_date
            admission.discharge.save()
            return Response({'status': 'Expected DOD updated successfully'})
        except Exception as e:
            print("🚨 DOD ERROR:", str(e))
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # ==========================================
    # 🌟 PHASE 2: Print Request Workflow
    # ==========================================
    
    # 1. Branch requests permission to print
    @action(detail=True, methods=['post'])
    def request_print(self, request, uhid=None):
        patient = self.get_object()
        adm_no = request.data.get('admNo')
        
        try:
            admission = patient.admissions.get(admNo=adm_no)
            if not hasattr(admission, 'billing'):
                Billing.objects.create(admission=admission)
                
            admission.billing.printStatus = 'PENDING'
            admission.billing.printRequestedAt = timezone.now()
            admission.billing.save()
            return Response({'status': 'Print request sent to Super Admin'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # 2. Super Admin approves or rejects the print
    @action(detail=True, methods=['post'])
    def resolve_print(self, request, uhid=None):
        patient = self.get_object()
        adm_no = request.data.get('admNo')
        action = request.data.get('action') # Should be 'APPROVED' or 'REJECTED'
        
        try:
            admission = patient.admissions.get(admNo=adm_no)
            admission.billing.printStatus = action
            admission.billing.save()
            return Response({'status': f'Print request {action}'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # 3. Super Admin Dashboard fetches all pending requests across all branches
    @action(detail=False, methods=['get'])
    def pending_prints(self, request):
        # Find all patients who have an admission with a 'PENDING' billing status
        pending_patients = Patient.objects.filter(admissions__billing__printStatus='PENDING').distinct()
        
        # We reuse your existing serializer to send the full patient objects back
        serializer = self.get_serializer(pending_patients, many=True)
        return Response(serializer.data)
    
    
# 🌟 NEW: This serves the Excel/CSV Master Data to the frontend
class ServiceMasterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceMaster.objects.all()
    serializer_class = ServiceMasterSerializer
    pagination_class = None # We want to send all prices at once, no pages