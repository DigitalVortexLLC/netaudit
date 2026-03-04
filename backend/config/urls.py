from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Allauth (headless API + OAuth callbacks)
    path("accounts/", include("allauth.urls")),
    path("_allauth/", include("allauth.headless.urls")),
    # DRF API
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("devices.urls")),
    path("api/v1/", include("rules.urls")),
    path("api/v1/", include("audits.urls")),
    path("api/v1/", include("settings.urls")),
    path("api/v1/notifications/", include("notifications.urls")),
    path("api/v1/", include("config_sources.urls")),
]
