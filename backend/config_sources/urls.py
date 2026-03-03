from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import NetmikoDeviceTypeViewSet

router = DefaultRouter()
router.register("netmiko-device-types", NetmikoDeviceTypeViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
