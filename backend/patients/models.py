from django.db import models
from django.utils import timezone

class Patient(models.Model):
    # Branch tracking
    BRANCH_CHOICES = [('LNM', 'Laxmi Nagar'), ('RYM', 'Raya')]
    branch_location = models.CharField(max_length=3, choices=BRANCH_CHOICES, default='LNM')
    
    # Auto-generated UHID
    uhid = models.CharField(max_length=25, unique=True, blank=True)
    
    # Demographics (Matching React state exactly)
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
    
    # Billing / Panel Info
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
        # 1. Save the model first to generate the raw PostgreSQL ID
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # 2. If it's a new patient, format the UHID and save again
        if is_new and not self.uhid:
            branch_prefix = "SHL" if self.branch_location == 'LNM' else "SHR"
            # Formats as SHL-000-1, SHL-000-1502, etc.
            self.uhid = f"{branch_prefix}-000-{self.id}"
            self.save(update_fields=['uhid'])

    def __str__(self):
        return f"{self.uhid} - {self.patientName}"

class Admission(models.Model):
    # The related_name='admissions' is the magic keyword that lets React find this inside the Patient object!
    patient = models.ForeignKey(Patient, related_name='admissions', on_delete=models.CASCADE)
    admNo = models.PositiveIntegerField()
    dateTime = models.DateTimeField(default=timezone.now) # Date of Admission
    
    class Meta:
        unique_together = ('patient', 'admNo') # A patient can't have two Admission #1s

    def __str__(self):
        return f"{self.patient.uhid} - Adm #{self.admNo}"

class MedicalHistory(models.Model):
    # One Admission has exactly One Medical History record
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
    expectedDod = models.DateField(null=True, blank=True)
    dod = models.DateTimeField(null=True, blank=True)
    dischargeStatus = models.CharField(max_length=100, blank=True)

class Service(models.Model):
    # One admission can have MANY services (bed charge, blood test, x-ray)
    admission = models.ForeignKey(Admission, related_name='services', on_delete=models.CASCADE)
    svcName = models.CharField(max_length=200)
    svcCat = models.CharField(max_length=100, blank=True)
    svcDate = models.DateField(null=True, blank=True)
    svcQty = models.PositiveIntegerField(default=1)
    svcRate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    svcTot = models.DecimalField(max_digits=10, decimal_places=2, default=0)

class Billing(models.Model):
    admission = models.OneToOneField(Admission, related_name='billing', on_delete=models.CASCADE)
    paymentMode = models.CharField(max_length=50, blank=True)
    paidNow = models.BooleanField(default=False)    

class ServiceMaster(models.Model):
    CATEGORY_CHOICES = [
        ('ICU CARE', 'ICU Care'),
        ('ROOM CHARGE', 'Room Charge'),
        ('CONSULTANT', 'Consultant'),
        ('RADIOLOGY', 'Radiology'),
        ('GENERAL SERVICES', 'General Services'),
    ]
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True)
    rate = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"[{self.category}] {self.description}"
