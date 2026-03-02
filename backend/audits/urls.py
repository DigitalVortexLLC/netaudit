from django.urls import include, path
from rest_framework.routers import DefaultRouter

from audits.views import AuditRunViewSet, AuditScheduleViewSet, DashboardSummaryView, TagViewSet

router = DefaultRouter()
router.register("audits", AuditRunViewSet, basename="auditrun")
router.register("schedules", AuditScheduleViewSet, basename="auditschedule")
router.register("tags", TagViewSet, basename="tag")

urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("", include(router.urls)),
]
