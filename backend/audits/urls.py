from django.urls import include, path
from rest_framework.routers import DefaultRouter

from audits.views import AuditRunViewSet, AuditScheduleViewSet, DashboardSummaryView

router = DefaultRouter()
router.register("audits", AuditRunViewSet, basename="auditrun")
router.register("schedules", AuditScheduleViewSet, basename="auditschedule")

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("", include(router.urls)),
]
