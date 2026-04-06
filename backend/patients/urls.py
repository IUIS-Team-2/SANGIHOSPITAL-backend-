from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatientViewSet, ServiceMasterViewSet

router = DefaultRouter()
router.register(r'patients', PatientViewSet)
router.register(r'service-master', ServiceMasterViewSet)

urlpatterns = [
    path('', include(router.urls)),
]