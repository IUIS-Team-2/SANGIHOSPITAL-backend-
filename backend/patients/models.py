from django.db import models
from django.utils import timezone
import datetime
from django.conf import settings
from users.models import CustomUser


class Patient(models.Model):
    BRANCH_CHOICES = [('LNM', 'Laxmi Nagar'), ('RYM', 'Raya')]
    branch_location = models.CharField(max_length=3, choices=BRANCH_CHOICES, default='LNM')
    uhid = models.CharField(max_length=25, unique=True, blank=True)
    
    patientName = models.CharField(max_length=150)
    guardianName = models.CharField(max_length=150)
    gender = models.CharField(max_length=15)
    dob = models.DateField(null=True, blank=True)
    bloodGroup = models.CharField(max_length=10, blank=True)
    maritalStatus = models.CharField(max_length=20, blank=True)
    phone = models.CharField(max_length=15)
    altPhone = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField()
    nationalId = models.CharField(max_length=50)
    remarks = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    
    payMode = models.CharField(max_length=20, default='cash')
    cashlessType = models.CharField(max_length=20, blank=True)
    tpa = models.CharField(max_length=100, blank=True)
    tpaCard = models.CharField(max_length=50, blank=True)
    tpaValidity = models.DateField(null=True, blank=True)
    tpaCardType = models.CharField(max_length=50, blank=True)
    tpaPanelCardNo = models.CharField(max_length=50, blank=True)
    tpaPanelValidity = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Generate UHID BEFORE saving to avoid double-saving
        if is_new and not self.uhid:
            branch_prefix = "SHL" if self.branch_location == 'LNM' else "SHR"
            
            # Count how many patients already exist IN THIS BRANCH
            branch_count = Patient.objects.filter(branch_location=self.branch_location).count()
            new_sequence = branch_count + 1
            
            # Formats to SHL-000-1, SHR-000-1, etc.
            self.uhid = f"{branch_prefix}-000-{new_sequence}"
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.uhid} - {self.patientName}"

class Admission(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='admissions')
    ipdNo = models.CharField(max_length=50, unique=True, blank=True)
    admNo = models.PositiveIntegerField()
    dateTime = models.DateTimeField(default=timezone.now) 
    
    class Meta:
        unique_together = ('patient', 'admNo') 

    def __str__(self):
        return f"{self.patient.uhid} - Adm #{self.admNo} ({self.ipdNo})"
    
    def save(self, *args, **kwargs):
        if not self.ipdNo:
            year = datetime.datetime.now().strftime('%y')
            prefix = f"SH/GEN/{year}/"
            last_admission = Admission.objects.filter(
                ipdNo__startswith=prefix
            ).order_by('-ipdNo').first()
            
            if last_admission:
                try:
                    last_sequence = int(last_admission.ipdNo.split('/')[-1])
                    new_sequence = last_sequence + 1
                except (ValueError, IndexError):
                    new_sequence = 1001
            else:
                new_sequence = 1001
            
            self.ipdNo = f"{prefix}{new_sequence}"
            
        super().save(*args, **kwargs)

class MedicalHistory(models.Model):
    admission = models.OneToOneField(Admission, related_name='medicalHistory', on_delete=models.CASCADE)
    previousDiagnosis = models.TextField(blank=True)
    pastSurgeries = models.TextField(blank=True)
    currentMedications = models.TextField(blank=True)
    treatingDoctor = models.CharField(max_length=150, blank=True)
    knownAllergies = models.TextField(blank=True)
    chronicConditions = models.TextField(blank=True)
    familyHistory = models.TextField(blank=True)
    smokingStatus = models.CharField(max_length=50, blank=True)
    alcoholUse = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)

class Discharge(models.Model):
    admission = models.OneToOneField(Admission, related_name='discharge', on_delete=models.CASCADE)

    department = models.CharField(max_length=100, blank=True)
    doctorName = models.CharField(max_length=150, blank=True)
    wardName = models.CharField(max_length=100, blank=True)
    roomNo = models.CharField(max_length=50, blank=True)
    bedNo = models.CharField(max_length=50, blank=True)
    diagnosis = models.TextField(blank=True)
    doa = models.DateTimeField(null=True, blank=True) 

    expectedDod = models.DateField(null=True, blank=True)
    dod = models.DateTimeField(null=True, blank=True)
    dischargeStatus = models.CharField(max_length=100, blank=True)

class Service(models.Model):    
    admission = models.ForeignKey('Admission', related_name='services', on_delete=models.CASCADE)
    pricing_applied = models.CharField(max_length=10, default='CASH')
    svcName = models.CharField(max_length=200)
    svcCat = models.CharField(max_length=100, blank=True)
    svcDate = models.DateField(null=True, blank=True)
    svcQty = models.PositiveIntegerField(default=1)
    svcRate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    svcTot = models.DecimalField(max_digits=10, decimal_places=2, default=0)

class Billing(models.Model):
    admission = models.ForeignKey('Admission', related_name='bills', on_delete=models.CASCADE)
    
    BILL_TYPE_CHOICES = [
        ('CASH', 'Cash'),
        ('CASHLESS', 'Cashless'),
    ]
    bill_type = models.CharField(max_length=20, choices=BILL_TYPE_CHOICES, default='CASH') # ✨ NEW
    
    paymentMode = models.CharField(max_length=50, blank=True)
    paidNow = models.BooleanField(default=False)  
    printStatus = models.CharField(max_length=50, default='DRAFT') 
    printRequestedAt = models.DateTimeField(null=True, blank=True)

class ServiceMaster(models.Model):
    CATEGORY_CHOICES = [
        ('ICU CARE', 'ICU Care'),
        ('ROOM CHARGE', 'Room Charge'),
        ('CONSULTANT', 'Consultant'),
        ('RADIOLOGY', 'Radiology'),
        ('GENERAL SERVICES', 'General Services'),
    ]
    
    PRICING_CHOICES = [
        ('CASH', 'Cash'),
        ('CASHLESS', 'Cashless'),
    ]
    
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    pricing_type = models.CharField(max_length=10, choices=PRICING_CHOICES, default='CASH') 
    description = models.TextField()
    code = models.CharField(max_length=50, blank=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"[{self.category}] {self.description} ({self.pricing_type})"

class DischargeSummary(models.Model):

    STATUS_CHOICES = [
        ('NORMAL', 'Normal'),
        ('LAMA', 'LAMA'),
        ('REFERRED', 'Referred'),
        ('DEATH', 'Death'),
        ('DOPR', 'dopr'),
    ]

    # Links directly to your existing Admission model
    admission = models.OneToOneField(Admission, on_delete=models.CASCADE, related_name='dynamic_summary')
    
    summary_type = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    # This JSON field holds the entire generated/edited template form
    content = models.JSONField(default=dict) 
    
    # Audit tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.summary_type} Summary for Adm No: {self.admission.admNo} (UHID: {self.admission.patient.uhid})"
    
class Task(models.Model):
    PRIORITY_CHOICES = (
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Urgent', 'Urgent'),
    )
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('On Hold', 'On Hold'),
    )
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    # Who assigned it? (Office Admin or HOD)
    assigned_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='tasks_given')
    
    # Who is doing it? (HOD or Staff)
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='tasks_received')
    
    # Which department does this task belong to?
    department = models.CharField(max_length=100) 
    
    # 🌟 MULTI-SELECT PATIENTS: Link the specific cashless patients to this task!
    patients = models.ManyToManyField(Patient, related_name='assigned_tasks')
    
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='Medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    due_date = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.assigned_to.username}"
    
class LabReport(models.Model):
    # Link it to the patient and the specific admission
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='lab_reports')
    admission = models.ForeignKey('Admission', on_delete=models.CASCADE, related_name='lab_reports', null=True, blank=True)
    
    report_name = models.CharField(max_length=255) # e.g., "KIDNEY FUNCTION TEST"
    
    # Stores the table rows [{"name": "BLOOD UREA", "value": "47", "normal": "(13-45 mg/dl)"}]
    table_data = models.JSONField(default=list)
    
    # Stores the pre-filled paragraphs [{"title": "COMMENTS", "text": "The typhidot test..."}]
    text_data = models.JSONField(default=list, blank=True)
    
    created_by = models.CharField(max_length=255, blank=True, null=True) # E.g., the receptionist's name
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.report_name} for {self.patient.uhid}"