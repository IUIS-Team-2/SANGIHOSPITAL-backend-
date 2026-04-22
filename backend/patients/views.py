import datetime
import csv
import json
from urllib.parse import quote
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from django.db import models
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from .models import (
    Patient,
    Admission,
    MedicalHistory,
    Discharge,
    Service,
    Billing,
    ServiceMaster,
    DischargeSummary,
    Task,
    LabReport,
    HODReview,
    DepartmentLogEntry,
)
from .serializers import (
    PatientSerializer,
    MedicalHistorySerializer,
    DischargeSerializer,
    ServiceSerializer,
    BillingSerializer,
    ServiceMasterSerializer,
    DischargeSummarySerializer,
    TaskSerializer,
    LabReportSerializer,
    HODReviewSerializer,
    DepartmentLogEntrySerializer,
)
import copy
from .templates import DISCHARGE_TEMPLATES
import io
from xhtml2pdf import pisa
from users.models import CustomUser

DEPARTMENT_ROLE_MAP = {
    'Billing': 'billing',
    'Uploading': 'uploading',
    'Query': 'query',
    'OPD': 'opd',
    'Intimation': 'intimation',
}

DEPARTMENT_LOG_FIELDS = {
    'opd': ['uploadDate', 'createdAt', 'opdDate'],
    'intimation': ['uploadDate', 'createdAt', 'doa'],
    'query': ['queryRepDate', 'createdAt', 'raiseDate'],
    'uploading': ['uploadDate', 'createdAt', 'doa'],
}

def normalize_task_status(raw_status, due_date=None):
    status_map = {
        'pending': 'Pending',
        'in-progress': 'In Progress',
        'completed': 'Completed',
        'on-hold': 'On Hold',
        'overdue': 'Overdue',
    }
    safe_status = status_map.get(str(raw_status or '').strip().lower(), 'Pending')
    if safe_status != 'Completed' and due_date and due_date < timezone.now():
        return 'Overdue'
    return safe_status

def serialize_task_for_hod(task):
    patient = task.patients.first()
    status_value = task.status
    if status_value != 'Completed' and task.due_date and task.due_date < timezone.now():
        status_value = 'Overdue'

    status_map = {
        'Pending': 'pending',
        'In Progress': 'in-progress',
        'Completed': 'completed',
        'On Hold': 'pending',
        'Overdue': 'overdue',
    }
    priority_map = {
        'Low': 'low',
        'Medium': 'medium',
        'High': 'high',
        'Urgent': 'high',
    }

    employee_name = task.assigned_to.get_full_name().strip() or task.assigned_to.username

    patient_type = 'TPA'
    if patient:
        if (patient.cashlessType or '').lower().find('card') >= 0:
            patient_type = 'Card'
        elif (patient.payMode or '').lower().find('cash') >= 0:
            patient_type = 'Cash'

    return {
        'id': task.id,
        'employeeId': task.assigned_to_id,
        'employeeName': employee_name,
        'taskType': task.title,
        'patientId': patient.uhid if patient else '',
        'patientType': patient_type,
        'priority': priority_map.get(task.priority, 'medium'),
        'dueDate': task.due_date.date().isoformat() if task.due_date else '',
        'status': status_map.get(status_value, 'pending'),
        'notes': task.description or '',
        'department': task.department,
    }

def get_department_role(department):
    return DEPARTMENT_ROLE_MAP.get(str(department or '').strip(), '')

def get_allowed_hod_departments(user):
    if user.role == 'superadmin':
        return list(DEPARTMENT_ROLE_MAP.keys())
    if user.role == 'office_admin':
        return list(DEPARTMENT_ROLE_MAP.keys())
    if user.role == 'hod':
        return list(DEPARTMENT_ROLE_MAP.keys())
    return []

def ensure_hod_access(request):
    role = getattr(request.user, 'role', '')
    if not request.user.is_authenticated or role not in ['hod', 'office_admin', 'superadmin']:
        return Response({'error': 'Unauthorized access.'}, status=status.HTTP_403_FORBIDDEN)
    return None

def coerce_record_date(department, payload):
    for key in DEPARTMENT_LOG_FIELDS.get(department, []):
        value = payload.get(key)
        if not value:
            continue
        if isinstance(value, str):
            safe_value = value[:10]
            try:
                return datetime.date.fromisoformat(safe_value)
            except ValueError:
                continue
    return timezone.localdate()

def get_or_create_current_billing(admission):
    billing = admission.bills.order_by('-id').first()
    if billing:
        return billing, False
    return Billing.objects.create(admission=admission), True

class PatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all().order_by('-created_at')
    serializer_class = PatientSerializer
    lookup_field = 'uhid'
    lookup_value_regex = '[^/]+' 


    def get_queryset(self):
        user = self.request.user
        queryset = Patient.objects.all()

        # 1. Super Admin & Office Admin see everything (Office admin filtered to cashless in JS)
        if user.role in ['superadmin', 'office_admin']:
            return queryset
            
        # 2. 🌟 THE FIX: Branch Admin AND Receptionists see their branch's patients!
        elif user.role in ['admin', 'receptionist']:
            return queryset.filter(branch_location=user.branch)
            
        # 3. HOD sees tasks assigned to them, OR tasks they assigned to their department
        elif user.role == 'hod':
            from django.db import models # Ensure models is imported for Q objects
            return queryset.filter(
                models.Q(assigned_tasks__assigned_to=user) | 
                models.Q(assigned_tasks__assigned_by=user)
            ).distinct()

        # 4. Staff only see patients explicitly assigned to them via Task Manager!
        elif user.role in ['billing', 'opd', 'intimation', 'query', 'uploading']:
            return queryset.filter(assigned_tasks__assigned_to=user).distinct()

        return queryset.none()
    
    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        admission_type = data.pop('admissionType', None) or request.data.get('admissionType') or 'IPD'
        
        if 'locId' in data:
            data['branch_location'] = 'RYM' if data['locId'] == 'raya' else 'LNM'
            
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        patient = serializer.instance 

        try:
            Admission.objects.create(patient=patient, admNo=1, admissionType=admission_type)
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
            billing_obj, _ = get_or_create_current_billing(admission_obj)
                
            for key, value in billing_data.items():
                # 🌟 PROTECT STATUS: Ignore printStatus so staff saves don't overwrite Admin approvals!
                if key in ['id', 'admission', 'printStatus', 'printRequestedAt']: 
                    continue
                    
                if key in ['discount', 'advance', 'paidNow']:
                    if value in ["", None]:
                        value = Decimal('0')
                    else:
                        try:
                            value = Decimal(str(value))
                        except (InvalidOperation, ValueError, TypeError):
                            value = Decimal('0')
                    
                setattr(billing_obj, key, value)

            pay_mode = str(getattr(patient, 'payMode', '') or '')
            billing_obj.bill_type = 'CASHLESS' if 'cashless' in pay_mode.lower() else 'CASH'
                
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
            
            if master_service:
                # 3. The Backend calculates the rate and total to prevent tampering
                svc_rate = master_service.rate
                svc_tot = svc_rate * svc_qty
                svc_cat = master_service.category
            else:
                raw_rate = service_data.get('svcRate') or service_data.get('rate') or 0
                raw_cat = service_data.get('svcCat') or service_data.get('type') or 'GENERAL SERVICES'
                try:
                    svc_rate = Decimal(str(raw_rate))
                except (InvalidOperation, ValueError, TypeError):
                    svc_rate = Decimal('0')
                svc_tot = svc_rate * svc_qty
                svc_cat = raw_cat

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
            admission_type = request.data.get('admissionType') or 'IPD'
            
            last_adm = Admission.objects.filter(patient=patient).order_by('id').last()
            new_adm_no = (last_adm.admNo + 1) if last_adm else 1
            
            
            admission = Admission.objects.create(
                patient=patient, 
                admNo=new_adm_no,
                admissionType=admission_type,
            )
            
            return Response({
                "message": "Admission created successfully", 
                "ipdNo": admission.ipdNo,
                "admNo": admission.admNo,
                "admissionType": admission.admissionType,
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
            billing_obj, _ = get_or_create_current_billing(admission)
            
            # 🌟 SMART CHECK: Prevent resetting an already approved bill back to PENDING!
            if billing_obj.printStatus == 'APPROVED':
                return Response({'status': 'Already approved'})

            billing_obj.printStatus = 'PENDING'
            billing_obj.printRequestedAt = timezone.now()
            billing_obj.save()
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
            billing_obj, _ = get_or_create_current_billing(admission)
            billing_obj.printStatus = action
            billing_obj.save()
                
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
        billing = admission.bills.order_by('-id').first()

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
    
class TaskReportAPIView(APIView):
    # Only Office Admin & HOD can view this report
    def get(self, request):
        # Find all staff under them
        staff = CustomUser.objects.filter(role__in=['billing', 'opd', 'intimation', 'query', 'uploading', 'hod'])
        
        report_data = []
        for employee in staff:
            # Count the tasks dynamically
            total_tasks = employee.tasks_received.count()
            completed_tasks = employee.tasks_received.filter(status='Completed').count()
            
            # Fetch the patients assigned to this employee
            assigned_patients = Patient.objects.filter(assigned_tasks__assigned_to=employee).distinct()
            patient_list = [{"uhid": p.uhid, "name": p.patientName} for p in assigned_patients]

            if total_tasks > 0:
                report_data.append({
                    "employee_name": f"{employee.first_name} {employee.last_name}",
                    "department": employee.role,
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "pending_tasks": total_tasks - completed_tasks,
                    "assigned_patients": patient_list
                })

        return Response(report_data)
    
class TaskListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer

    def get_queryset(self):
        user = self.request.user
        # Office Admin sees all tasks
        if user.role in ['superadmin', 'office_admin']:
            return Task.objects.all()
        # HOD sees tasks they created OR tasks assigned to them
        elif user.role == 'hod':
            return Task.objects.filter(models.Q(assigned_to=user) | models.Q(assigned_by=user))
        # Staff only see tasks assigned to them
        return Task.objects.filter(assigned_to=user)

    def perform_create(self, serializer):
        # When an Admin/HOD creates a task, automatically set them as the "assigned_by" person
        serializer.save(assigned_by=self.request.user)

class TaskDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TaskSerializer
    queryset = Task.objects.all()

class LabReportListCreateView(generics.ListCreateAPIView):
    serializer_class = LabReportSerializer

    def get_queryset(self):
        uhid = self.kwargs.get('uhid')
        adm_no = self.kwargs.get('adm_no')
        return LabReport.objects.filter(patient__uhid=uhid, admission__admNo=adm_no)

    def perform_create(self, serializer):
        uhid = self.kwargs.get('uhid')
        adm_no = self.kwargs.get('adm_no')
        
        # 1. Safely find the exact Patient and Admission from the database
        patient = get_object_or_404(Patient, uhid=uhid)
        admission = get_object_or_404(Admission, patient=patient, admNo=adm_no)
        
        # 2. Save the report and link it automatically!
        serializer.save(
            patient=patient, 
            admission=admission,
            created_by=self.request.user.first_name or self.request.user.username
        )

class HODEmployeeListAPIView(APIView):
    def get(self, request):
        denied = ensure_hod_access(request)
        if denied:
            return denied

        department = request.query_params.get('department')
        role_slug = get_department_role(department)
        queryset = CustomUser.objects.filter(role=role_slug)

        if getattr(request.user, 'branch', None) in ['LNM', 'RYM']:
            queryset = queryset.filter(branch=request.user.branch)

        employees = []
        for employee in queryset.order_by('first_name', 'username'):
            tasks = employee.tasks_received.filter(department=department)
            employee_name = employee.get_full_name().strip() or employee.username
            employees.append({
                'id': employee.id,
                'name': employee_name,
                'email': employee.email,
                'role': employee.role,
                'department': department,
                'taskCount': tasks.count(),
            })

        return Response({'employees': employees}, status=status.HTTP_200_OK)

class HODTaskListCreateAPIView(APIView):
    def get(self, request):
        denied = ensure_hod_access(request)
        if denied:
            return denied

        department = request.query_params.get('department')
        employee_id = request.query_params.get('employeeId')
        date_filter = request.query_params.get('date')
        status_filter = request.query_params.get('status')

        tasks = Task.objects.select_related('assigned_to').prefetch_related('patients').filter(department=department)

        if getattr(request.user, 'branch', None) in ['LNM', 'RYM']:
            tasks = tasks.filter(
                models.Q(assigned_to__branch=request.user.branch) |
                models.Q(assigned_to__branch__isnull=True)
            )

        if employee_id:
            tasks = tasks.filter(assigned_to_id=employee_id)
        if date_filter:
            tasks = tasks.filter(created_at__date=date_filter)

        serialized = [serialize_task_for_hod(task) for task in tasks.order_by('-created_at')]
        if status_filter:
            serialized = [task for task in serialized if task['status'] == status_filter]

        return Response({'tasks': serialized}, status=status.HTTP_200_OK)

    def post(self, request):
        denied = ensure_hod_access(request)
        if denied:
            return denied

        employee_id = request.data.get('employeeId')
        department = request.data.get('department')
        assigned_to = get_object_or_404(CustomUser, pk=employee_id)
        due_date_raw = request.data.get('dueDate')
        due_date = None
        if due_date_raw:
            due_date = timezone.make_aware(datetime.datetime.fromisoformat(f"{due_date_raw}T23:59:00"))

        priority_map = {'low': 'Low', 'medium': 'Medium', 'high': 'High'}
        task = Task.objects.create(
            title=request.data.get('taskType') or 'Task',
            description=request.data.get('notes') or '',
            assigned_by=request.user,
            assigned_to=assigned_to,
            department=department,
            priority=priority_map.get(str(request.data.get('priority')).lower(), 'Medium'),
            status=normalize_task_status(request.data.get('status') or 'pending', due_date),
            due_date=due_date,
        )

        patient_uhid = request.data.get('patientId')
        if patient_uhid:
            patient = Patient.objects.filter(uhid=patient_uhid).first()
            if patient:
                task.patients.add(patient)

        return Response({'task': serialize_task_for_hod(task)}, status=status.HTTP_201_CREATED)

class HODTaskDetailAPIView(APIView):
    def patch(self, request, pk):
        denied = ensure_hod_access(request)
        if denied:
            return denied

        task = get_object_or_404(Task, pk=pk)
        due_date = task.due_date
        if 'priority' in request.data:
            priority_map = {'low': 'Low', 'medium': 'Medium', 'high': 'High'}
            task.priority = priority_map.get(str(request.data.get('priority')).lower(), task.priority)
        if 'notes' in request.data:
            task.description = request.data.get('notes') or ''
        if 'status' in request.data:
            task.status = normalize_task_status(request.data.get('status'), due_date)
        task.save()
        return Response({'task': serialize_task_for_hod(task)}, status=status.HTTP_200_OK)

class HODAnalyticsAPIView(APIView):
    def get(self, request):
        denied = ensure_hod_access(request)
        if denied:
            return denied

        department = request.query_params.get('department')
        employee_id = request.query_params.get('employeeId')
        date_filter = request.query_params.get('date')

        tasks = Task.objects.select_related('assigned_to').filter(department=department)
        if getattr(request.user, 'branch', None) in ['LNM', 'RYM']:
            tasks = tasks.filter(assigned_to__branch=request.user.branch)
        if employee_id:
            tasks = tasks.filter(assigned_to_id=employee_id)
        if date_filter:
            tasks = tasks.filter(created_at__date=date_filter)

        task_rows = [serialize_task_for_hod(task) for task in tasks]
        total = len(task_rows)
        completed = sum(1 for task in task_rows if task['status'] == 'completed')
        pending = sum(1 for task in task_rows if task['status'] == 'pending')
        overdue = sum(1 for task in task_rows if task['status'] == 'overdue')

        stats = [
            {'label': 'Total Tasks', 'value': total, 'sub': f'{department or "All"} department'},
            {'label': 'Completed', 'value': completed, 'sub': 'Marked complete'},
            {'label': 'Pending', 'value': pending, 'sub': 'Awaiting action'},
            {'label': 'Overdue', 'value': overdue, 'sub': 'Past due date'},
        ]

        employee_stats = []
        for employee in CustomUser.objects.filter(role=get_department_role(department)):
            employee_tasks = [task for task in task_rows if task['employeeId'] == employee.id]
            if not employee_tasks and employee_id:
                continue
            assigned = len(employee_tasks)
            emp_completed = sum(1 for task in employee_tasks if task['status'] == 'completed')
            emp_pending = sum(1 for task in employee_tasks if task['status'] == 'pending')
            emp_overdue = sum(1 for task in employee_tasks if task['status'] == 'overdue')
            employee_stats.append({
                'id': employee.id,
                'name': employee.get_full_name().strip() or employee.username,
                'assigned': assigned,
                'completed': emp_completed,
                'pending': emp_pending,
                'overdue': emp_overdue,
                'completionPct': int(round((emp_completed / assigned) * 100)) if assigned else 0,
            })

        return Response({'stats': stats, 'employeeStats': employee_stats}, status=status.HTTP_200_OK)

class HODReviewListCreateAPIView(APIView):
    def get(self, request):
        denied = ensure_hod_access(request)
        if denied:
            return denied

        department = request.query_params.get('department')
        reviews = HODReview.objects.select_related('employee', 'reviewed_by').filter(department=department).order_by('-created_at')

        if getattr(request.user, 'branch', None) in ['LNM', 'RYM']:
            reviews = reviews.filter(employee__branch=request.user.branch)

        payload = []
        for review in reviews:
            payload.append({
                'id': review.id,
                'employeeName': review.employee.get_full_name().strip() or review.employee.username,
                'employeeId': review.employee_id,
                'period': review.period,
                'rating': review.rating,
                'performanceScore': review.performance_score,
                'comments': review.comments,
                'submittedAt': timezone.localtime(review.created_at).strftime('%Y-%m-%d %H:%M'),
            })
        return Response({'reviews': payload}, status=status.HTTP_200_OK)

    def post(self, request):
        denied = ensure_hod_access(request)
        if denied:
            return denied

        employee = get_object_or_404(CustomUser, pk=request.data.get('employeeId'))
        review = HODReview.objects.create(
            department=request.data.get('department') or '',
            employee=employee,
            reviewed_by=request.user,
            period=request.data.get('period') or 'weekly',
            rating=int(request.data.get('rating') or 5),
            performance_score=str(request.data.get('performanceScore') or ''),
            comments=request.data.get('comments') or '',
            task_name=request.data.get('taskName') or 'Department Performance',
        )
        serializer = HODReviewSerializer(review)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class HODReportDownloadAPIView(APIView):
    def get(self, request):
        denied = ensure_hod_access(request)
        if denied:
            return denied

        department = request.query_params.get('department')
        employee_id = request.query_params.get('employeeId')
        date_filter = request.query_params.get('date')

        tasks = Task.objects.select_related('assigned_to').prefetch_related('patients').filter(department=department)
        if employee_id:
            tasks = tasks.filter(assigned_to_id=employee_id)
        if date_filter:
            tasks = tasks.filter(created_at__date=date_filter)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{quote((department or "department").lower())}_tasks_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Task ID', 'Employee', 'Task', 'Patient UHID', 'Priority', 'Status', 'Due Date'])
        for task in tasks.order_by('-created_at'):
            data = serialize_task_for_hod(task)
            writer.writerow([
                data['id'],
                data['employeeName'],
                data['taskType'],
                data['patientId'],
                data['priority'],
                data['status'],
                data['dueDate'],
            ])
        return response

class PerformanceRatingsAPIView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Unauthorized access.'}, status=status.HTTP_401_UNAUTHORIZED)

        reviews = HODReview.objects.select_related('employee', 'reviewed_by').order_by('-created_at')
        payload = []
        for review in reviews:
            branch = 'laxmi' if review.employee.branch == 'LNM' else 'raya'
            payload.append({
                'staffName': review.employee.get_full_name().strip() or review.employee.username,
                'staffId': review.employee.emp_id or review.employee.username,
                'branch': branch,
                'role': review.employee.get_role_display(),
                'department': review.department,
                'task': review.task_name or 'Department Performance',
                'rating': review.rating,
                'reviewedBy': review.reviewed_by.get_full_name().strip() if review.reviewed_by else 'System',
                'description': review.comments,
                'reason': '',
                'date': timezone.localtime(review.created_at).date().isoformat(),
            })
        return Response(payload, status=status.HTTP_200_OK)

class DepartmentLogListAPIView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Unauthorized access.'}, status=status.HTTP_401_UNAUTHORIZED)

        department = request.query_params.get('department')
        queryset = DepartmentLogEntry.objects.filter(department=department)

        if getattr(request.user, 'branch', None) in ['LNM', 'RYM']:
            queryset = queryset.filter(branch=request.user.branch)

        serializer = DepartmentLogEntrySerializer(queryset.order_by('-record_date', '-created_at'), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class DepartmentLogBulkSaveAPIView(APIView):
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Unauthorized access.'}, status=status.HTTP_401_UNAUTHORIZED)

        department = request.data.get('department')
        entries = request.data.get('entries') or []
        if department not in dict(DepartmentLogEntry.DEPARTMENT_CHOICES):
            return Response({'error': 'Invalid department.'}, status=status.HTTP_400_BAD_REQUEST)

        branch = getattr(request.user, 'branch', None) if getattr(request.user, 'branch', None) in ['LNM', 'RYM'] else (request.data.get('branch') or 'LNM')
        record_dates = sorted({coerce_record_date(department, entry) for entry in entries})

        with transaction.atomic():
            if record_dates:
                DepartmentLogEntry.objects.filter(
                    department=department,
                    branch=branch,
                    record_date__in=record_dates,
                ).delete()

            created = []
            for entry in entries:
                created.append(DepartmentLogEntry(
                    department=department,
                    branch=branch,
                    record_date=coerce_record_date(department, entry),
                    data=entry,
                    created_by=request.user,
                ))
            if created:
                DepartmentLogEntry.objects.bulk_create(created)

        return Response({'saved': len(entries)}, status=status.HTTP_200_OK)
