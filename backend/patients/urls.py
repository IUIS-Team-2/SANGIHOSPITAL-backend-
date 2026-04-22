from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatientViewSet, PrintDischargeSummaryView, ServiceMasterViewSet, DynamicDischargeSummaryView
from .views import TaskListCreateAPIView, TaskDetailAPIView, TaskReportAPIView
from .views import LabReportListCreateView

router = DefaultRouter()
router.register(r'patients', PatientViewSet)
router.register(r'service-master', ServiceMasterViewSet)

urlpatterns = [
    path('patients/<str:uhid>/admissions/<str:adm_no>/dynamic-summary/', DynamicDischargeSummaryView.as_view(), name='dynamic-summary'),
    path('', include(router.urls)),
    path('patients/<str:uhid>/admissions/<str:adm_no>/dynamic-summary/print/', PrintDischargeSummaryView.as_view(), name='print-summary'),
    path('tasks/', TaskListCreateAPIView.as_view(), name='task-list-create'),
    path('tasks/<int:pk>/', TaskDetailAPIView.as_view(), name='task-detail'),
    path('tasks/report/', TaskReportAPIView.as_view(), name='task-report'),
    path('patients/<str:uhid>/admissions/<int:adm_no>/lab-reports/', LabReportListCreateView.as_view(), name='lab-reports'),
]