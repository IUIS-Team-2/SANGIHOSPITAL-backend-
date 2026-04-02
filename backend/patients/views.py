from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction  # 🌟 NEW: Needed for the new_admission action
from .models import Patient, Admission, ServiceMaster  # 🌟 NEW: Added ServiceMaster
from .serializers import (
    PatientSerializer, MedicalHistorySerializer, 
    DischargeSerializer, ServiceSerializer, BillingSerializer,
    ServiceMasterSerializer  # 🌟 NEW: Added ServiceMasterSerializer
)

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all().order_by('-created_at')
    serializer_class = PatientSerializer
    lookup_field = 'uhid'
    
    # 🌟 THE SECRET SAUCE: This tells Django that UHIDs can contain dashes!
    lookup_value_regex = '[^/]+' 

    @action(detail=True, methods=['patch'])
    def update_medical(self, request, uhid=None):
        patient = self.get_object()
        adm_no = request.data.get('admNo')
        medical_data = request.data.get('medicalData')
        try:
            admission = patient.admissions.get(admNo=adm_no)
            ser = MedicalHistorySerializer(admission.medicalHistory, data=medical_data, partial=True)
            if ser.is_valid():
                ser.save()
                return Response({'status': 'Medical history updated'})
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=404)

    @action(detail=True, methods=['patch'])
    def discharge(self, request, uhid=None):
        patient = self.get_object()
        adm_no = request.data.get('admNo')
        discharge_data = request.data.get('dischargeData')
        try:
            admission = patient.admissions.get(admNo=adm_no)
            ser = DischargeSerializer(admission.discharge, data=discharge_data, partial=True)
            if ser.is_valid():
                ser.save()
                return Response({'status': 'Discharged successfully'})
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=404)

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

    @action(detail=True, methods=['patch'])
    def update_billing(self, request, uhid=None):
        patient = self.get_object()
        adm_no = request.data.get('admNo')
        billing_data = request.data.get('billingData')
        try:
            admission = patient.admissions.get(admNo=adm_no)
            ser = BillingSerializer(admission.billing, data=billing_data, partial=True)
            if ser.is_valid():
                ser.save()
                return Response({'status': 'Billing updated'})
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=404)
        
    # 🌟 NEW: Start a new Admission for a returning patient
    @action(detail=True, methods=['post'])
    def new_admission(self, request, uhid=None):
        patient = self.get_object()
        
        # Find the highest admission number and add 1
        last_adm = patient.admissions.order_by('-admNo').first()
        new_adm_no = (last_adm.admNo + 1) if last_adm else 1
        
        with transaction.atomic():
            admission = Admission.objects.create(patient=patient, admNo=new_adm_no)
            
            MedicalHistory.objects.create(admission=admission)
            Discharge.objects.create(admission=admission)
            Billing.objects.create(admission=admission)
            
            return Response({
                'status': f'New Admission #{new_adm_no} started successfully',
                'uhid': patient.uhid,
                'admNo': new_adm_no
            })

# 🌟 NEW: This serves the Excel/CSV Master Data to the frontend
class ServiceMasterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceMaster.objects.all()
    serializer_class = ServiceMasterSerializer
    pagination_class = None # We want to send all prices at once, no pages