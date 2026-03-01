from django.urls import path

from . import views_html

urlpatterns = [
    path("", views_html.settings_view, name="settings-html"),
]
