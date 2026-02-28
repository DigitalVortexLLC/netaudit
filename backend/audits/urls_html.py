from django.urls import path

from . import views_html

urlpatterns = [
    path("", views_html.DashboardView.as_view(), name="dashboard"),
    path("audits/", views_html.AuditRunListView.as_view(), name="auditrun-list-html"),
    path("audits/<int:pk>/", views_html.AuditRunDetailView.as_view(), name="auditrun-detail-html"),
    path("audits/<int:pk>/status/", views_html.audit_run_status_fragment, name="auditrun-status-fragment"),
    path("audits/<int:pk>/config/", views_html.audit_run_config, name="auditrun-config-fragment"),
]
