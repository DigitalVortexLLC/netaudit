from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import WebhookProviderViewSet

router = DefaultRouter()
router.register("webhooks", WebhookProviderViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
