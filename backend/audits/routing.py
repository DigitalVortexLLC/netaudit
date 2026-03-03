"""WebSocket URL routing for audit consumers."""

from django.urls import re_path

from audits.consumers import AuditDetailConsumer, DashboardConsumer

websocket_urlpatterns = [
    re_path(r"ws/dashboard/$", DashboardConsumer.as_asgi()),
    re_path(r"ws/audits/(?P<audit_id>\d+)/$", AuditDetailConsumer.as_asgi()),
]
