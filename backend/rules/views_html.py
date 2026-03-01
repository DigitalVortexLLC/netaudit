import ast

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView

from accounts.decorators import RoleRequiredMixin, role_required

from .forms import CustomRuleForm, SimpleRuleForm
from .models import CustomRule, SimpleRule


# ---------------------------------------------------------------------------
# Simple Rules
# ---------------------------------------------------------------------------


class SimpleRuleListView(LoginRequiredMixin, ListView):
    model = SimpleRule
    template_name = "rules/simplerule_list.html"
    context_object_name = "rules"


class SimpleRuleCreateView(RoleRequiredMixin, CreateView):
    min_role = "editor"

    model = SimpleRule
    form_class = SimpleRuleForm
    template_name = "rules/simplerule_form.html"
    success_url = reverse_lazy("simplerule-list-html")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Simple rule created successfully.")
        return response


class SimpleRuleUpdateView(RoleRequiredMixin, UpdateView):
    min_role = "editor"

    model = SimpleRule
    form_class = SimpleRuleForm
    template_name = "rules/simplerule_form.html"
    success_url = reverse_lazy("simplerule-list-html")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Simple rule updated successfully.")
        return response


@role_required("editor")
@require_POST
def simple_rule_delete(request, pk):
    rule = get_object_or_404(SimpleRule, pk=pk)
    rule.delete()
    messages.success(request, "Simple rule deleted successfully.")
    return redirect("simplerule-list-html")


# ---------------------------------------------------------------------------
# Custom Rules
# ---------------------------------------------------------------------------


class CustomRuleListView(LoginRequiredMixin, ListView):
    model = CustomRule
    template_name = "rules/customrule_list.html"
    context_object_name = "rules"


class CustomRuleCreateView(RoleRequiredMixin, CreateView):
    min_role = "editor"

    model = CustomRule
    form_class = CustomRuleForm
    template_name = "rules/customrule_form.html"
    success_url = reverse_lazy("customrule-list-html")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Custom rule created successfully.")
        return response


class CustomRuleUpdateView(RoleRequiredMixin, UpdateView):
    min_role = "editor"

    model = CustomRule
    form_class = CustomRuleForm
    template_name = "rules/customrule_form.html"
    success_url = reverse_lazy("customrule-list-html")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Custom rule updated successfully.")
        return response


@role_required("editor")
@require_POST
def custom_rule_delete(request, pk):
    rule = get_object_or_404(CustomRule, pk=pk)
    rule.delete()
    messages.success(request, "Custom rule deleted successfully.")
    return redirect("customrule-list-html")


@role_required("viewer")
@require_POST
def custom_rule_validate(request, pk):
    rule = get_object_or_404(CustomRule, pk=pk)
    try:
        ast.parse(rule.content)
        return render(
            request,
            "rules/partials/validate_result.html",
            {"valid": True},
        )
    except SyntaxError as exc:
        return render(
            request,
            "rules/partials/validate_result.html",
            {"valid": False, "error": str(exc)},
        )
