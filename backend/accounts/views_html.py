from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views import generic

from .decorators import RoleRequiredMixin
from .forms import ProfileForm, UserRoleForm

User = get_user_model()


class ProfileView(LoginRequiredMixin, generic.UpdateView):
    model = User
    form_class = ProfileForm
    template_name = "accounts/profile.html"

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Profile updated.")
        return redirect("profile")


class UserListView(RoleRequiredMixin, generic.ListView):
    min_role = "admin"
    model = User
    template_name = "accounts/user_list.html"
    context_object_name = "users"
    queryset = User.objects.all().order_by("username")


class UserUpdateRoleView(RoleRequiredMixin, generic.UpdateView):
    min_role = "admin"
    model = User
    form_class = UserRoleForm
    template_name = "accounts/user_edit.html"
    context_object_name = "target_user"

    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, f'User "{user.username}" updated.')
        return redirect("user-list")
