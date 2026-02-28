from datetime import timedelta

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from .forms import AuditScheduleForm
from .models import AuditRun, AuditSchedule


class DashboardView(TemplateView):
    template_name = "audits/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
            pass_rate = (
                round(passed_count / total_tests * 100, 1) if total_tests > 0 else 0.0
            )
        else:
            pass_rate = 0.0

        recent_audits = AuditRun.objects.select_related("device").all()[:10]

        context.update(
            {
                "device_count": device_count,
                "recent_audit_count": recent_audit_count,
                "pass_rate": pass_rate,
                "recent_audits": recent_audits,
            }
        )
        return context


class AuditRunListView(ListView):
    model = AuditRun
    template_name = "audits/auditrun_list.html"
    context_object_name = "auditrun_list"
    queryset = AuditRun.objects.select_related("device")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from devices.models import Device

        context["devices"] = Device.objects.all()
        return context


class AuditRunDetailView(DetailView):
    model = AuditRun
    template_name = "audits/auditrun_detail.html"
    context_object_name = "object"
    queryset = AuditRun.objects.select_related("device")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["results"] = self.object.results.all()
        context["has_config"] = bool(self.object.config_snapshot)
        return context


@require_GET
def audit_run_status_fragment(request, pk):
    from django.template.response import TemplateResponse

    audit_run = get_object_or_404(AuditRun, pk=pk)
    return TemplateResponse(
        request,
        "audits/partials/auditrun_status.html",
        {"audit_run": audit_run},
    )


@require_GET
def audit_run_config(request, pk):
    from django.template.response import TemplateResponse

    audit_run = get_object_or_404(AuditRun, pk=pk)
    return TemplateResponse(
        request,
        "audits/partials/config_viewer.html",
        {"config_snapshot": audit_run.config_snapshot},
    )


class ScheduleListView(ListView):
    model = AuditSchedule
    template_name = "audits/schedule_list.html"
    context_object_name = "schedule_list"
    queryset = AuditSchedule.objects.select_related("device")


class ScheduleCreateView(CreateView):
    model = AuditSchedule
    form_class = AuditScheduleForm
    template_name = "audits/schedule_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        from audits.tasks import create_schedule

        create_schedule(self.object)
        messages.success(self.request, f'Schedule "{self.object.name}" created.')
        return response

    def get_success_url(self):
        from django.urls import reverse

        return reverse("schedule-list-html")


class ScheduleUpdateView(UpdateView):
    model = AuditSchedule
    form_class = AuditScheduleForm
    template_name = "audits/schedule_form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        from audits.tasks import create_schedule, delete_schedule

        delete_schedule(self.object)
        create_schedule(self.object)
        messages.success(self.request, f'Schedule "{self.object.name}" updated.')
        return response

    def get_success_url(self):
        from django.urls import reverse

        return reverse("schedule-list-html")


@require_POST
def schedule_delete(request, pk):
    schedule = get_object_or_404(AuditSchedule, pk=pk)
    name = schedule.name
    from audits.tasks import delete_schedule

    delete_schedule(schedule)
    schedule.delete()
    messages.success(request, f'Schedule "{name}" deleted.')
    return redirect("schedule-list-html")
