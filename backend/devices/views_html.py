import requests as http_requests
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views import generic
from django.views.decorators.http import require_POST

from accounts.decorators import RoleRequiredMixin, role_required
from audits.tasks import enqueue_audit

from .forms import DeviceForm, DeviceGroupForm, DeviceHeaderFormSet
from .models import Device, DeviceGroup


class DeviceGroupListView(generic.ListView):
    model = DeviceGroup
    template_name = "devices/group_list.html"
    context_object_name = "groups"

    def get_queryset(self):
        return DeviceGroup.objects.prefetch_related("devices").all()


class DeviceGroupCreateView(generic.CreateView):
    model = DeviceGroup
    form_class = DeviceGroupForm
    template_name = "devices/group_form.html"

    def form_valid(self, form):
        group = form.save()
        messages.success(self.request, f'Group "{group.name}" created.')
        return redirect("group-list-html")


class DeviceGroupUpdateView(generic.UpdateView):
    model = DeviceGroup
    form_class = DeviceGroupForm
    template_name = "devices/group_form.html"

    def form_valid(self, form):
        group = form.save()
        messages.success(self.request, f'Group "{group.name}" updated.')
        return redirect("group-list-html")


class DeviceGroupDetailView(generic.DetailView):
    model = DeviceGroup
    template_name = "devices/group_detail.html"
    context_object_name = "group"

    def get_queryset(self):
        return DeviceGroup.objects.prefetch_related("devices")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        group = self.object
        ctx["devices"] = group.devices.all()
        ctx["simple_rules"] = group.simple_rules.all()
        ctx["custom_rules"] = group.custom_rules.all()
        return ctx


@require_POST
def group_delete(request, pk):
    group = get_object_or_404(DeviceGroup, pk=pk)
    name = group.name
    group.delete()
    messages.success(request, f'Group "{name}" deleted.')
    return redirect("group-list-html")


@require_POST
def group_run_audit(request, pk):
    group = get_object_or_404(DeviceGroup, pk=pk)
    devices = group.devices.filter(enabled=True)
    count = 0
    for device in devices:
        enqueue_audit(device.id, trigger="manual")
        count += 1
    html = render_to_string(
        "devices/partials/audit_started.html",
        {"device": None, "group": group, "count": count},
    )
    return HttpResponse(html)


class DeviceListView(LoginRequiredMixin, generic.ListView):
    model = Device
    template_name = "devices/device_list.html"
    context_object_name = "devices"

    def get_queryset(self):
        return Device.objects.prefetch_related("headers", "groups").all()


class DeviceCreateView(RoleRequiredMixin, generic.CreateView):
    min_role = "editor"

    model = Device
    form_class = DeviceForm
    template_name = "devices/device_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["header_formset"] = DeviceHeaderFormSet(
                self.request.POST, prefix="headers"
            )
        else:
            ctx["header_formset"] = DeviceHeaderFormSet(prefix="headers")
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        header_formset = ctx["header_formset"]
        if header_formset.is_valid():
            device = form.save()
            header_formset.instance = device
            header_formset.save()
            messages.success(self.request, f'Device "{device.name}" created.')
            return redirect("device-list-html")
        return self.form_invalid(form)


class DeviceUpdateView(RoleRequiredMixin, generic.UpdateView):
    min_role = "editor"

    model = Device
    form_class = DeviceForm
    template_name = "devices/device_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.POST:
            ctx["header_formset"] = DeviceHeaderFormSet(
                self.request.POST, instance=self.object, prefix="headers"
            )
        else:
            ctx["header_formset"] = DeviceHeaderFormSet(
                instance=self.object, prefix="headers"
            )
        return ctx

    def form_valid(self, form):
        ctx = self.get_context_data()
        header_formset = ctx["header_formset"]
        if header_formset.is_valid():
            device = form.save()
            header_formset.instance = device
            header_formset.save()
            messages.success(self.request, f'Device "{device.name}" updated.')
            return redirect("device-list-html")
        return self.form_invalid(form)


class DeviceDetailView(LoginRequiredMixin, generic.DetailView):
    model = Device
    template_name = "devices/device_detail.html"
    context_object_name = "device"

    def get_queryset(self):
        return Device.objects.prefetch_related("headers", "groups")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        device = self.object
        ctx["recent_audits"] = device.audit_runs.order_by("-created_at")[:10]
        ctx["simple_rules"] = device.simple_rules.all()
        ctx["custom_rules"] = device.custom_rules.all()
        return ctx


@role_required("editor")
@require_POST
def device_delete(request, pk):
    device = get_object_or_404(Device, pk=pk)
    name = device.name
    device.delete()
    messages.success(request, f'Device "{name}" deleted.')
    return redirect("device-list-html")


@role_required("editor")
@require_POST
def device_test_connection(request, pk):
    device = get_object_or_404(Device, pk=pk)
    endpoint = device.effective_api_endpoint
    if not endpoint:
        html = render_to_string(
            "devices/partials/test_result.html",
            {
                "success": False,
                "error": "No API endpoint configured and no default endpoint is set.",
            },
        )
        return HttpResponse(html)
    headers = {h.key: h.value for h in device.headers.all()}
    try:
        response = http_requests.get(endpoint, headers=headers, timeout=10)
        html = render_to_string(
            "devices/partials/test_result.html",
            {
                "success": True,
                "status_code": response.status_code,
                "content_length": len(response.content),
            },
        )
    except http_requests.RequestException as exc:
        html = render_to_string(
            "devices/partials/test_result.html",
            {
                "success": False,
                "error": str(exc),
            },
        )
    return HttpResponse(html)


@role_required("editor")
@require_POST
def device_run_audit(request, pk):
    device = get_object_or_404(Device, pk=pk)
    enqueue_audit(device.id, trigger="manual")
    html = render_to_string(
        "devices/partials/audit_started.html",
        {
            "device": device,
        },
    )
    return HttpResponse(html)


@role_required("editor")
def device_header_add(request):
    index = request.GET.get("index", "0")
    html = render_to_string(
        "devices/partials/header_form_row.html",
        {
            "index": index,
            "prefix": "headers",
        },
    )
    return HttpResponse(html)
