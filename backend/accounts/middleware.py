from django.conf import settings
from django.utils.module_loading import import_string


class ApiCsrfExemptMiddleware:
    """Skip CSRF enforcement for all /api/ paths (JWT-authenticated API)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/"):
            request._dont_enforce_csrf_checks = True
        return self.get_response(request)


class AuthHookMiddleware:
    """Pluggable auth hook middleware.

    Loads hook classes from settings.AUTH_HOOKS and calls their methods
    at three points: pre_authenticate, post_authenticate, on_response.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._hooks = self._load_hooks()

    def _load_hooks(self):
        hook_paths = getattr(settings, "AUTH_HOOKS", [])
        hooks = []
        for path in hook_paths:
            hook_class = import_string(path)
            hooks.append(hook_class())
        return hooks

    def __call__(self, request):
        # Pre-authenticate hooks
        for hook in self._hooks:
            pre = getattr(hook, "pre_authenticate", None)
            if pre:
                result = pre(request)
                if result is not None:
                    return result

        # Post-authenticate hooks (user is resolved by AuthenticationMiddleware)
        for hook in self._hooks:
            post = getattr(hook, "post_authenticate", None)
            if post:
                result = post(request)
                if result is not None:
                    return result

        response = self.get_response(request)

        # Response hooks
        for hook in self._hooks:
            on_resp = getattr(hook, "on_response", None)
            if on_resp:
                on_resp(request, response)

        return response
