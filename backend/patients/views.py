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
    ServiceMaster,
    DischargeSummary
)
from .serializers import (
    PatientSerializer, 
    MedicalHistorySerializer, 
    DischargeSerializer, 
    ServiceSerializer, 
    BillingSerializer,
    ServiceMasterSerializer,
    DischargeSummarySerializer
)
import copy
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .templates import DISCHARGE_TEMPLATES
import io
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa 

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all().order_by('-created_at')
    serializer_class = PatientSerializer
    lookup_field = 'uhid'
    lookup_value_regex = '[^/]+' 

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        
        if 'locId' in data:
            data['branch_location'] = 'RYM' if data['locId'] == 'raya' else 'LNM'
            
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        patient = serializer.instance 

        try:
            Admission.objects.create(patient=patient, admNo=1)
            response_serializer = self.get_serializer(patient)
            headers = self.get_success_headers(response_serializer.data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            print("🚨 AUTO-ADMISSION FAILED:", str(e))
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch'])
    def update_medical(self, request, uhid=None):
        patient = self.get_object()
        adm_no = request.data.get('admNo') or 1
        medical_data = request.data.get('medicalData', {})
        
        try:
            admission_obj, _ = Admission.objects.get_or_create(patient=patient, admNo=adm_no)
            med_hist, _ = MedicalHistory.objects.get_or_create(admission=admission_obj)
                
            for key, value in medical_data.items():
                if key in ['id', 'admission']:
                    continue
                setattr(med_hist, key, value)
                
            med_hist.save()
            return Response({'status': 'Medical history updated successfully'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['patch'])
    def discharge(self, request, uhid=None):
        patient = self.get_object()
        adm_no = request.data.get('admNo') or 1
        discharge_data = request.data.get('dischargeData', {})
        
        try:
            admission_obj, _ = Admission.objects.get_or_create(patient=patient, admNo=adm_no)
            discharge_obj, _ = Discharge.objects.get_or_create(admission=admission_obj)
                
            for key, value in discharge_data.items():
                if key in ['id', 'admission']: 
                    continue
                if key in ['dod', 'expectedDod', 'actualDod'] and value == "":
                    value = None
                setattr(discharge_obj, key, value)
                
            discharge_obj.save()
            return Response({'status': 'Discharge updated successfully'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=True, methods=['patch'])
    def update_billing(self, request, uhid=None):
        patient = self.get_object()
        adm_no = request.data.get('admNo') or 1
        billing_data = request.data.get('billingData', {})
        
        try:
            admission_obj, _ = Admission.objects.get_or_create(patient=patient, admNo=adm_no)
            billing_obj, _ = Billing.objects.get_or_create(admission=admission_obj)
                
            for key, value in billing_data.items():
                # 🌟 PROTECT STATUS: Ignore printStatus so staff saves don't overwrite Admin approvals!
                if key in ['id', 'admission', 'printStatus', 'printRequestedAt']: 
                    continue
                    
                if key == 'paidNow' and value == "":
                    value = False
                elif key == 'paidNow' and isinstance(value, str):
                    value = value.lower() == "true"
                    
                setattr(billing_obj, key, value)
                
            billing_obj.save()
            return Response({'status': 'Billing updated successfully'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def add_service(self, request, uhid=None):
        patient = self.get_object()
        adm_no = request.data.get('admNo') or 1
        service_data = request.data.get('serviceData')
        
        try:
            admission_obj, _ = Admission.objects.get_or_create(patient=patient, admNo=adm_no)
            
            # 1. Extract the secure, basic data sent from the frontend
            svc_name = service_data.get('svcName')
            # Look for the pricing type (defaults to CASH if not provided)
            pricing_applied = service_data.get('pricing_type', 'CASH').upper() 
            svc_qty = int(service_data.get('svcQty', 1))
            svc_date = service_data.get('svcDate')
            
            if not svc_name:
                return Response({'error': 'Service name (svcName) is required.'}, status=status.HTTP_400_BAD_REQUEST)
                
            # ✨ 2. AUTOMATED SECURE PRICING LOGIC
            # Query the ServiceMaster DB to get the correct rate based on the pricing type
            from .models import ServiceMaster # Ensuring it's imported
            
            master_service = ServiceMaster.objects.filter(
                description__iexact=svc_name, 
                pricing_type=pricing_applied
            ).first()
            
            if not master_service:
                return Response({
                    'error': f"Service '{svc_name}' with pricing '{pricing_applied}' not found in the master tariff list."
                }, status=status.HTTP_400_BAD_REQUEST)
                
            # 3. The Backend calculates the rate and total to prevent tampering
            svc_rate = master_service.rate
            svc_tot = svc_rate * svc_qty
            svc_cat = master_service.category
            
            # 4. Save the service with the newly fetched data
            service, created = Service.objects.update_or_create(
                admission=admission_obj,
                svcName=svc_name,  
                pricing_applied=pricing_applied, # We use this in the lookup to separate Cash vs Cashless updates
                defaults={
                    'svcCat': svc_cat,
                    'svcQty': svc_qty,
                    'svcRate': svc_rate,
                    'svcTot': svc_tot,
                    'svcDate': svc_date
                }
            )
            
            from .serializers import ServiceSerializer # Ensuring serializer is ready
            return Response({
                'status': 'Service added successfully with automated pricing.', 
                'data': ServiceSerializer(service).data
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
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

    @action(detail=True, methods=['post'])
    def request_print(self, request, uhid=None):
        patient = self.get_object()
        adm_no = request.data.get('admNo')
        
        try:
            admission = patient.admissions.get(admNo=adm_no)
            
            # 🌟 SMART CHECK: Prevent resetting an already approved bill back to PENDING!
            if hasattr(admission, 'billing') and admission.billing.printStatus == 'APPROVED':
                return Response({'status': 'Already approved'})
                
            if not hasattr(admission, 'billing'):
                Billing.objects.create(admission=admission)
                
            admission.billing.printStatus = 'PENDING'
            admission.billing.printRequestedAt = timezone.now()
            admission.billing.save()
            return Response({'status': 'Print request sent to Super Admin'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def resolve_print(self, request, uhid=None):
        patient = self.get_object()
        adm_no = request.data.get('admNo')
        
        action = request.data.get('action') or request.data.get('status') or request.data.get('backendAction') or 'APPROVED'
        
        try:
            admission = patient.admissions.get(admNo=adm_no)
            if hasattr(admission, 'billing'):
                admission.billing.printStatus = action
                admission.billing.save()
            else:
                Billing.objects.create(admission=admission, printStatus=action)
                
            return Response({'status': f'Print request {action}'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def pending_prints(self, request):
        pending_patients = Patient.objects.filter(admissions__bills__printStatus='PENDING').distinct()
        
        serializer = self.get_serializer(pending_patients, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='cashless-records')
    def cashless_records(self, request):
        # 1. Strict Security Check: Only Office Admins can hit this endpoint
        if getattr(request.user, 'role', '') != 'office_admin':
            return Response(
                {"error": "Unauthorized access. Only Office Admins can view the corporate dashboard."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 2. Database Query: Find patients linked to an admission that has a cashless bill
        # The .distinct() ensures we don't get duplicate patients if they have multiple cashless visits
        from .models import Patient
        cashless_patients = Patient.objects.filter(admissions__bills__bill_type='CASHLESS').distinct()
        
        # 3. Serialize and Return
        # Because the user is 'office_admin', our updated serializer will naturally 
        # expose all the prices and totals we hid from the hospital staff!
        serializer = self.get_serializer(cashless_patients, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class ServiceMasterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceMaster.objects.all()
    serializer_class = ServiceMasterSerializer
    pagination_class = None 

class DynamicDischargeSummaryView(APIView):
    def _clean_status(self, raw_status):
        status_str = str(raw_status).upper()
        if "LAMA" in status_str: return "LAMA"
        if "DOPR" in status_str: return "DOPR"
        if "REFER" in status_str: return "REFER"
        if "DEATH" in status_str: return "DEATH"
        return "NORMAL"

    def get(self, request, uhid, adm_no):
        raw_type = request.query_params.get('type', 'NORMAL')
        summary_type = self._clean_status(raw_type)
        admission = get_object_or_404(Admission, patient__uhid=uhid, admNo=adm_no)

        existing_summary = DischargeSummary.objects.filter(admission=admission).first()
        if existing_summary:
            return Response({
                "is_existing": True,
                "summary_type": existing_summary.summary_type,
                "content": existing_summary.content
            }, status=status.HTTP_200_OK)

        template = copy.deepcopy(DISCHARGE_TEMPLATES.get(summary_type, DISCHARGE_TEMPLATES["NORMAL"]))

        # 🌟 UPDATED PRE-FILL: Iterate through the List to find keys
        try:
            med_hist = getattr(admission, 'medicalHistory', None)
            if med_hist:
                for section in template["sections"]:
                    if section["key"] == "k_c_o" and med_hist.previousDiagnosis:
                        section["value"] = med_hist.previousDiagnosis
        except Exception:
            pass

        return Response({"is_existing": False, "summary_type": summary_type, "content": template}, status=status.HTTP_200_OK)

    def post(self, request, uhid, adm_no):
        admission = get_object_or_404(Admission, patient__uhid=uhid, admNo=adm_no)
        raw_type = request.data.get('summary_type', 'NORMAL')
        summary_type = self._clean_status(raw_type)
        content = request.data.get('content', {})

        summary, created = DischargeSummary.objects.update_or_create(
            admission=admission,
            defaults={'summary_type': summary_type, 'content': content, 'created_by': request.user if request.user.is_authenticated else None}
        )
        return Response({"message": "Discharge Summary saved successfully!", "data": DischargeSummarySerializer(summary).data}, status=status.HTTP_200_OK)

class PrintDischargeSummaryView(APIView):
    def get(self, request, uhid, adm_no):
        admission = get_object_or_404(Admission, patient__uhid=uhid, admNo=adm_no)
        summary = get_object_or_404(DischargeSummary, admission=admission)
        
        status_map = {"NORMAL": "pdf/normal.html", "RECOVERED": "pdf/normal.html", "LAMA": "pdf/lama.html", "REFER": "pdf/refer.html", "DOPR": "pdf/dopr.html", "DEATH": "pdf/death.html"}
        template_file = status_map.get(summary.summary_type, "pdf/normal.html")
        
        patient = admission.patient
        discharge = getattr(admission, 'discharge', None)
        billing = getattr(admission, 'billing', None)

        age = "--"
        if patient.dob:
            calc_age = (timezone.now().date() - patient.dob).days // 365
            age = f"{calc_age} YRS"

        sections = summary.content.get("sections", [])

        # 🌟 NEW: BACKEND AUTO-CONVERTER 🌟
        # If an old database record is an Object/Dict, convert it to a List format instantly!
        if isinstance(sections, dict):
            sections = [{"key": k, **v} for k, v in sections.items()]

        # Now we can safely iterate through the list without crashing
        if discharge:
            for section in sections:
                if section.get("key") == "condition_at_discharge":
                    section["value"] = discharge.dischargeStatus.upper() if discharge.dischargeStatus else "--"

        context = {
            "s": summary, "sections": sections,
            "ipd_no": admission.ipdNo, "patient_name": patient.patientName.upper(),
            "guardian_name": patient.guardianName.upper() if patient.guardianName else "--",
            "address": patient.address, "consultant": discharge.doctorName.upper() if discharge and discharge.doctorName else "--",
            "claim_id": patient.tpaPanelCardNo if patient.tpaPanelCardNo else "--",
            "doa": admission.dateTime.strftime("%d-%m-%Y %H:%M HRS") if admission.dateTime else "--",
            "dod": discharge.dod.strftime("%d-%m-%Y %H:%M HRS") if (discharge and discharge.dod) else "--",
            "bill_no": f"{billing.id}/{admission.dateTime.strftime('%y')}" if billing else "--",
            "bill_date": discharge.dod.strftime("%d-%m-%Y %H:%M HRS") if (discharge and discharge.dod) else "--",
            "age_sex": f"{age} / {patient.gender.upper()}", "card_no": patient.tpaCard if patient.tpaCard else "--",
            "room": f"{discharge.roomNo} / {discharge.wardName.upper()}" if discharge and discharge.roomNo else "-- / --",
            "panel": patient.tpa.upper() if patient.tpa else patient.payMode.upper(),
            "contact_no": patient.phone, "status_on_discharge": discharge.dischargeStatus.upper() if discharge and discharge.dischargeStatus else "--",
        }

        html_string = render_to_string(template_file, context)
        result = io.BytesIO()
        pdf = pisa.pisaDocument(io.BytesIO(html_string.encode("UTF-8")), result)
        
        if not pdf.err:
            response = HttpResponse(result.getvalue(), content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="{uhid}_summary.pdf"'
            return response
            
        return Response({"error": "PDF Generation Failed"}, status=400)