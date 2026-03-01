from django.urls import path

from . import views

urlpatterns = [
    path("settings/", views.site_settings_view, name="site-settings"),
]
