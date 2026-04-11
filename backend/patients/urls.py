from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatientViewSet, PrintDischargeSummaryView, ServiceMasterViewSet, DynamicDischargeSummaryView

router = DefaultRouter()
router.register(r'patients', PatientViewSet)
router.register(r'service-master', ServiceMasterViewSet)

urlpatterns = [
    path('patients/<str:uhid>/admissions/<str:adm_no>/dynamic-summary/', DynamicDischargeSummaryView.as_view(), name='dynamic-summary'),
    path('', include(router.urls)),
    path('patients/<str:uhid>/admissions/<str:adm_no>/dynamic-summary/print/', PrintDischargeSummaryView.as_view(), name='print-summary'),
]