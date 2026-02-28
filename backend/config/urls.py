from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Authentication (allauth HTML views)
    path("accounts/", include("allauth.urls")),
    path("accounts/", include("accounts.urls_html")),
    # DRF API
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("devices.urls")),
    path("api/v1/", include("rules.urls")),
    path("api/v1/", include("audits.urls")),
    # HTML views
    path("", include("audits.urls_html")),
    path("devices/", include("devices.urls_html")),
    path("rules/", include("rules.urls_html")),
    path("schedules/", include("audits.urls_html_schedules")),
]
