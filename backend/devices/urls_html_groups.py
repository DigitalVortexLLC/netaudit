from django.urls import path

from . import views_html

urlpatterns = [
    path("", views_html.DeviceGroupListView.as_view(), name="group-list-html"),
    path("new/", views_html.DeviceGroupCreateView.as_view(), name="group-create-html"),
    path("<int:pk>/", views_html.DeviceGroupDetailView.as_view(), name="group-detail-html"),
    path("<int:pk>/edit/", views_html.DeviceGroupUpdateView.as_view(), name="group-update-html"),
    path("<int:pk>/delete/", views_html.group_delete, name="group-delete-html"),
    path("<int:pk>/run-audit/", views_html.group_run_audit, name="group-run-audit-html"),
]
