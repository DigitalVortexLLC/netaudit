from django.urls import path

from . import views_html

urlpatterns = [
    path("", views_html.DeviceListView.as_view(), name="device-list-html"),
    path("new/", views_html.DeviceCreateView.as_view(), name="device-create-html"),
    path("<int:pk>/", views_html.DeviceDetailView.as_view(), name="device-detail-html"),
    path(
        "<int:pk>/edit/",
        views_html.DeviceUpdateView.as_view(),
        name="device-update-html",
    ),
    path(
        "<int:pk>/delete/",
        views_html.device_delete,
        name="device-delete-html",
    ),
    path(
        "<int:pk>/test-connection/",
        views_html.device_test_connection,
        name="device-test-connection-html",
    ),
    path(
        "<int:pk>/run-audit/",
        views_html.device_run_audit,
        name="device-run-audit-html",
    ),
    path(
        "header-form/",
        views_html.device_header_add,
        name="device-header-add",
    ),
]
