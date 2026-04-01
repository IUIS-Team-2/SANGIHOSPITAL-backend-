from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Patient, Admission
from .serializers import (
    PatientSerializer, MedicalHistorySerializer, 
    DischargeSerializer, ServiceSerializer, BillingSerializer
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