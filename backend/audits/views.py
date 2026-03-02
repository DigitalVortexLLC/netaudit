from datetime import timedelta

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsEditorOrAbove, IsViewerOrAbove
from audits.models import AuditComment, AuditRun, AuditSchedule, RuleResult, Tag
from audits.serializers import (
    AuditCommentSerializer,
    AuditRunCreateSerializer,
    AuditRunDetailSerializer,
    AuditRunListSerializer,
    AuditScheduleSerializer,
    RuleResultSerializer,
    TagSerializer,
)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_permissions(self):
        if self.action == "list":
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]


class AuditRunViewSet(viewsets.ModelViewSet):
    queryset = AuditRun.objects.select_related("device").prefetch_related(
        "tags", "comments__author"
    )
    filterset_fields = ["device", "status", "trigger", "tags"]

    def get_permissions(self):
        if self.action in ("list", "retrieve", "results", "config"):
            return [IsViewerOrAbove()]
        if self.action in ("manage_tags", "manage_comments"):
            if self.request.method == "GET":
                return [IsViewerOrAbove()]
            return [IsEditorOrAbove()]
        if self.action in ("remove_tag", "manage_comment"):
            return [IsEditorOrAbove()]
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

    @action(detail=True, methods=["get", "post"], url_path="tags")
    def manage_tags(self, request, pk=None):
        audit_run = self.get_object()
        if request.method == "GET":
            serializer = TagSerializer(audit_run.tags.all(), many=True)
            return Response(serializer.data)
        tag_id = request.data.get("tag_id")
        tag_name = request.data.get("name")
        if tag_id:
            try:
                tag = Tag.objects.get(pk=tag_id)
            except Tag.DoesNotExist:
                return Response(
                    {"detail": "Tag not found."}, status=status.HTTP_404_NOT_FOUND
                )
        elif tag_name:
            tag, _ = Tag.objects.get_or_create(name=tag_name.strip()[:50])
        else:
            return Response(
                {"detail": "Provide tag_id or name."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        audit_run.tags.add(tag)
        return Response(TagSerializer(tag).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="tags/(?P<tag_id>[^/.]+)")
    def remove_tag(self, request, pk=None, tag_id=None):
        audit_run = self.get_object()
        try:
            tag = Tag.objects.get(pk=tag_id)
        except Tag.DoesNotExist:
            return Response(
                {"detail": "Tag not found."}, status=status.HTTP_404_NOT_FOUND
            )
        audit_run.tags.remove(tag)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get", "post"], url_path="comments")
    def manage_comments(self, request, pk=None):
        audit_run = self.get_object()
        if request.method == "GET":
            comments = audit_run.comments.select_related("author").all()
            serializer = AuditCommentSerializer(comments, many=True)
            return Response(serializer.data)
        serializer = AuditCommentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(audit_run=audit_run, author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=["put", "delete"],
        url_path="comments/(?P<comment_id>[^/.]+)",
    )
    def manage_comment(self, request, pk=None, comment_id=None):
        audit_run = self.get_object()
        try:
            comment = audit_run.comments.get(pk=comment_id)
        except AuditComment.DoesNotExist:
            return Response(
                {"detail": "Comment not found."}, status=status.HTTP_404_NOT_FOUND
            )
        if comment.author != request.user:
            return Response(
                {"detail": "You can only edit your own comments."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if request.method == "DELETE":
            comment.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = AuditCommentSerializer(comment, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


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

        failed_rule_count_24h = RuleResult.objects.filter(
            outcome=RuleResult.Outcome.FAILED,
            audit_run__completed_at__gte=last_24h,
        ).count()

        return Response(
            {
                "device_count": device_count,
                "recent_audit_count": recent_audit_count,
                "pass_rate": pass_rate,
                "failed_rule_count_24h": failed_rule_count_24h,
            }
        )
