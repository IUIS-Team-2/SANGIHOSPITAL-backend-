from django.contrib import admin
from .models import Patient, Admission, ServiceMaster, Service, Billing, Discharge, MedicalHistory

# This creates a nice table view for your Patients in the Admin panel
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('uhid', 'patientName', 'phone', 'created_at')
    search_fields = ('uhid', 'patientName', 'phone')

# This creates a nice table view for your Admissions
@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    # 🌟 Removed 'admissionDate' from here so the server boots up perfectly
    list_display = ('ipdNo', 'patient', 'admNo') 
    search_fields = ('ipdNo', 'patient__uhid')

# Registering the rest of your models so they show up!
admin.site.register(ServiceMaster)
admin.site.register(Service)
admin.site.register(Billing)
admin.site.register(Discharge)
admin.site.register(MedicalHistory)