from django.urls import path

from . import views

urlpatterns = [
    path("settings/", views.site_settings_view, name="site-settings"),
    path("settings/test-slack/", views.test_slack_view, name="test-slack"),
    path("settings/registration-status/", views.registration_status_view, name="registration-status"),
]
