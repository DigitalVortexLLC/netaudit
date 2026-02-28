from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from .permissions import ROLE_HIERARCHY


def role_required(min_role):
    """Decorator for HTML views requiring a minimum role."""
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            user_level = ROLE_HIERARCHY.get(request.user.role, 0)
            required_level = ROLE_HIERARCHY[min_role]
            if user_level < required_level:
                return HttpResponseForbidden("Insufficient permissions.")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class RoleRequiredMixin:
    """Mixin for class-based HTML views requiring a minimum role."""
    min_role = "viewer"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect("account_login")
        user_level = ROLE_HIERARCHY.get(request.user.role, 0)
        required_level = ROLE_HIERARCHY[self.min_role]
        if user_level < required_level:
            return HttpResponseForbidden("Insufficient permissions.")
        return super().dispatch(request, *args, **kwargs)
