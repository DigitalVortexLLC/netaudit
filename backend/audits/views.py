from datetime import timedelta

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsEditorOrAbove, IsViewerOrAbove
from audits.models import AuditRun, AuditSchedule
from audits.serializers import (
    AuditRunCreateSerializer,
    AuditRunDetailSerializer,
    AuditRunListSerializer,
    AuditScheduleSerializer,
    RuleResultSerializer,
)


class AuditRunViewSet(viewsets.ModelViewSet):
    queryset = AuditRun.objects.select_related("device")
    filterset_fields = ["device", "status", "trigger"]

    def get_permissions(self):
        if self.action in ("list", "retrieve", "results", "config"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]

    def get_serializer_class(self):
        if self.action == "create":
            return AuditRunCreateSerializer
        if self.action == "list":
            return AuditRunListSerializer
        return AuditRunDetailSerializer

    def perform_create(self, serializer):
        device = serializer.validated_data["device"]
        audit_run = AuditRun.objects.create(
            device=device,
            status=AuditRun.Status.PENDING,
            trigger=AuditRun.Trigger.MANUAL,
        )
        # Enqueue the audit task asynchronously.
        from audits.tasks import enqueue_audit

        enqueue_audit(device.id, trigger="manual")
        serializer.instance = audit_run

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        output_serializer = AuditRunDetailSerializer(serializer.instance)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def results(self, request, pk=None):
        audit_run = self.get_object()
        results = audit_run.results.all()
        serializer = RuleResultSerializer(results, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def config(self, request, pk=None):
        audit_run = self.get_object()
        return Response({"config": audit_run.config_snapshot})


class AuditScheduleViewSet(viewsets.ModelViewSet):
    queryset = AuditSchedule.objects.all()
    serializer_class = AuditScheduleSerializer
    filterset_fields = ["device", "enabled"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]

    def perform_create(self, serializer):
        instance = serializer.save()
        from audits.tasks import create_schedule

        create_schedule(instance)

    def perform_destroy(self, instance):
        from audits.tasks import delete_schedule

        delete_schedule(instance)
        instance.delete()


class DashboardSummaryView(APIView):
    permission_classes = [IsViewerOrAbove]

    def get(self, request):
        from devices.models import Device

        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        device_count = Device.objects.count()
        recent_audit_count = AuditRun.objects.filter(
            created_at__gte=last_24h,
        ).count()

        completed_recent = AuditRun.objects.filter(
            status=AuditRun.Status.COMPLETED,
            completed_at__gte=last_7d,
        )
        total_completed = completed_recent.count()

        if total_completed > 0:
            passed_count = 0
            total_tests = 0
            for audit in completed_recent:
                if audit.summary:
                    passed_count += audit.summary.get("passed", 0)
                    total_tests += sum(audit.summary.values())
            pass_rate = round(passed_count / total_tests * 100, 1) if total_tests > 0 else 0.0
        else:
            pass_rate = 0.0

        return Response(
            {
                "device_count": device_count,
                "recent_audit_count": recent_audit_count,
                "pass_rate": pass_rate,
            }
        )
