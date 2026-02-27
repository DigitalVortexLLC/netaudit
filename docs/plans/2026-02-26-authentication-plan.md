# Authentication & User Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add user authentication with passkey support, JWT API tokens, RBAC (admin/editor/viewer), and pluggable auth middleware to the netaudit Django app.

**Architecture:** django-allauth with built-in WebAuthn/passkey MFA, djangorestframework-simplejwt for API JWT tokens, dj-rest-auth bridging allauth and DRF. Custom User model with a `role` field synced to Django groups via signal. Custom `AuthHookMiddleware` with pluggable hook classes.

**Tech Stack:** Django 5.1, django-allauth[mfa] 65.x, djangorestframework-simplejwt 5.x, dj-rest-auth 7.x, fido2 (transitive via allauth)

**Design doc:** `docs/plans/2026-02-26-authentication-design.md`

---

### Task 1: Install Dependencies

**Files:**
- Modify: `backend/requirements.txt`

**Step 1: Add new packages to requirements.txt**

Add these three lines to `backend/requirements.txt` after the existing entries:

```
django-allauth[mfa]>=65.0,<66.0
dj-rest-auth>=7.0,<8.0
djangorestframework-simplejwt>=5.3,<6.0
```

**Step 2: Install packages**

Run: `pip install -r backend/requirements.txt`
Expected: All packages install without errors.

**Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "feat: add auth dependencies (allauth, simplejwt, dj-rest-auth)"
```

---

### Task 2: Create accounts app with custom User model

**Files:**
- Create: `backend/accounts/__init__.py`
- Create: `backend/accounts/apps.py`
- Create: `backend/accounts/models.py`
- Create: `backend/accounts/admin.py`
- Create: `backend/accounts/tests.py` (start with model tests)
- Modify: `backend/config/settings/base.py:15-33` (INSTALLED_APPS) and add AUTH_USER_MODEL

**Step 1: Create the app directory**

Run: `mkdir -p backend/accounts`

**Step 2: Write the User model test**

Create `backend/accounts/tests.py`:

```python
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

User = get_user_model()


class UserModelTests(TestCase):
    def test_create_user_defaults_to_viewer(self):
        user = User.objects.create_user(
            username="viewer1", email="viewer1@test.com", password="testpass123"
        )
        self.assertEqual(user.role, "viewer")
        self.assertTrue(user.is_api_enabled)

    def test_create_user_with_admin_role(self):
        user = User.objects.create_user(
            username="admin1", email="admin1@test.com", password="testpass123",
            role="admin",
        )
        self.assertEqual(user.role, "admin")

    def test_create_user_with_editor_role(self):
        user = User.objects.create_user(
            username="editor1", email="editor1@test.com", password="testpass123",
            role="editor",
        )
        self.assertEqual(user.role, "editor")

    def test_user_str(self):
        user = User.objects.create_user(
            username="testuser", email="test@test.com", password="testpass123"
        )
        self.assertEqual(str(user), "testuser")

    def test_invalid_role_rejected(self):
        user = User(username="bad", email="bad@test.com", role="superadmin")
        with self.assertRaises(Exception):
            user.full_clean()

    def test_created_at_set_on_create(self):
        user = User.objects.create_user(
            username="ts1", email="ts1@test.com", password="testpass123"
        )
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)
```

**Step 3: Run tests to verify they fail**

Run: `cd backend && python manage.py test accounts.tests.UserModelTests --verbosity=2 2>&1 | head -30`
Expected: FAIL — accounts app doesn't exist yet, model not defined.

**Step 4: Create the app files**

Create `backend/accounts/__init__.py` (empty file).

Create `backend/accounts/apps.py`:

```python
from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        import accounts.signals  # noqa: F401
```

Create `backend/accounts/models.py`:

```python
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        EDITOR = "editor", "Editor"
        VIEWER = "viewer", "Viewer"

    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.VIEWER,
    )
    is_api_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username
```

Create `backend/accounts/signals.py` (placeholder — implemented in Task 3):

```python
# Role-to-group sync signal — implemented in Task 3.
```

Create `backend/accounts/admin.py`:

```python
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "is_active", "date_joined")
    list_filter = BaseUserAdmin.list_filter + ("role",)
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Netaudit", {"fields": ("role", "is_api_enabled")}),
    )
```

**Step 5: Update settings**

In `backend/config/settings/base.py`:

Add `"accounts"` to INSTALLED_APPS (before `"devices"`):

```python
    # Local apps
    "accounts",
    "devices",
```

Add after AUTH_PASSWORD_VALIDATORS (line 72):

```python
AUTH_USER_MODEL = "accounts.User"
```

**Step 6: Create and run migration**

Run: `cd backend && python manage.py makemigrations accounts`
Expected: Creates `accounts/migrations/0001_initial.py`

**Important:** Since we're adding a custom user model to an existing project with data, we need to reset the database (dev uses SQLite). Delete `backend/db.sqlite3` and re-run all migrations:

Run: `rm -f backend/db.sqlite3 && cd backend && python manage.py migrate`
Expected: All migrations apply cleanly.

**Step 7: Run tests to verify they pass**

Run: `cd backend && python manage.py test accounts.tests.UserModelTests --verbosity=2`
Expected: All 6 tests PASS.

**Step 8: Commit**

```bash
git add backend/accounts/ backend/config/settings/base.py
git commit -m "feat: add accounts app with custom User model and RBAC role field"
```

---

### Task 3: Role-to-group sync signal

**Files:**
- Modify: `backend/accounts/signals.py`
- Modify: `backend/accounts/tests.py` (add signal tests)

**Step 1: Write the failing test**

Add to `backend/accounts/tests.py`:

```python
class RoleGroupSyncTests(TestCase):
    def test_saving_user_creates_group_and_adds_membership(self):
        user = User.objects.create_user(
            username="g1", email="g1@test.com", password="testpass123",
            role="editor",
        )
        self.assertTrue(Group.objects.filter(name="editor").exists())
        self.assertTrue(user.groups.filter(name="editor").exists())

    def test_changing_role_updates_group(self):
        user = User.objects.create_user(
            username="g2", email="g2@test.com", password="testpass123",
            role="viewer",
        )
        self.assertTrue(user.groups.filter(name="viewer").exists())
        user.role = "admin"
        user.save()
        user.refresh_from_db()
        self.assertTrue(user.groups.filter(name="admin").exists())
        self.assertFalse(user.groups.filter(name="viewer").exists())

    def test_role_group_has_no_extra_groups(self):
        user = User.objects.create_user(
            username="g3", email="g3@test.com", password="testpass123",
            role="admin",
        )
        role_groups = {"admin", "editor", "viewer"}
        user_groups = set(user.groups.values_list("name", flat=True))
        # User should only be in their role group (among role groups)
        self.assertEqual(user_groups & role_groups, {"admin"})
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test accounts.tests.RoleGroupSyncTests --verbosity=2`
Expected: FAIL — signal not implemented.

**Step 3: Implement the signal**

Replace `backend/accounts/signals.py`:

```python
from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def sync_role_to_group(sender, instance, **kwargs):
    """Keep the user's Django group in sync with their role field."""
    role_group_names = {choice[0] for choice in User.Role.choices}
    # Remove user from all role groups
    role_groups = Group.objects.filter(name__in=role_group_names)
    instance.groups.remove(*role_groups)
    # Add user to current role group
    group, _ = Group.objects.get_or_create(name=instance.role)
    instance.groups.add(group)
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python manage.py test accounts.tests.RoleGroupSyncTests --verbosity=2`
Expected: All 3 tests PASS.

**Step 5: Commit**

```bash
git add backend/accounts/signals.py backend/accounts/tests.py
git commit -m "feat: add signal to sync user role to Django group"
```

---

### Task 4: Permission classes and role_required decorator

**Files:**
- Create: `backend/accounts/permissions.py`
- Create: `backend/accounts/decorators.py`
- Modify: `backend/accounts/tests.py` (add permission tests)

**Step 1: Write failing tests for permissions**

Add to `backend/accounts/tests.py`:

```python
from unittest.mock import Mock

from rest_framework.test import APIRequestFactory

from accounts.permissions import IsAdminRole, IsEditorOrAbove, IsViewerOrAbove


class PermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = User.objects.create_user(
            username="padmin", email="padmin@test.com", password="testpass123",
            role="admin",
        )
        self.editor = User.objects.create_user(
            username="peditor", email="peditor@test.com", password="testpass123",
            role="editor",
        )
        self.viewer = User.objects.create_user(
            username="pviewer", email="pviewer@test.com", password="testpass123",
            role="viewer",
        )

    def _request_for(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_admin_permission(self):
        perm = IsAdminRole()
        self.assertTrue(perm.has_permission(self._request_for(self.admin), None))
        self.assertFalse(perm.has_permission(self._request_for(self.editor), None))
        self.assertFalse(perm.has_permission(self._request_for(self.viewer), None))

    def test_editor_or_above_permission(self):
        perm = IsEditorOrAbove()
        self.assertTrue(perm.has_permission(self._request_for(self.admin), None))
        self.assertTrue(perm.has_permission(self._request_for(self.editor), None))
        self.assertFalse(perm.has_permission(self._request_for(self.viewer), None))

    def test_viewer_or_above_permission(self):
        perm = IsViewerOrAbove()
        self.assertTrue(perm.has_permission(self._request_for(self.admin), None))
        self.assertTrue(perm.has_permission(self._request_for(self.editor), None))
        self.assertTrue(perm.has_permission(self._request_for(self.viewer), None))

    def test_unauthenticated_denied(self):
        request = self.factory.get("/")
        request.user = Mock(is_authenticated=False)
        self.assertFalse(IsViewerOrAbove().has_permission(request, None))
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test accounts.tests.PermissionTests --verbosity=2`
Expected: FAIL — permissions module not created.

**Step 3: Implement permissions**

Create `backend/accounts/permissions.py`:

```python
from rest_framework.permissions import BasePermission

ROLE_HIERARCHY = {"admin": 3, "editor": 2, "viewer": 1}


class _RolePermission(BasePermission):
    min_role = "viewer"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        user_level = ROLE_HIERARCHY.get(request.user.role, 0)
        required_level = ROLE_HIERARCHY[self.min_role]
        return user_level >= required_level


class IsAdminRole(_RolePermission):
    min_role = "admin"


class IsEditorOrAbove(_RolePermission):
    min_role = "editor"


class IsViewerOrAbove(_RolePermission):
    min_role = "viewer"
```

**Step 4: Implement role_required decorator**

Create `backend/accounts/decorators.py`:

```python
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
```

**Step 5: Run tests to verify they pass**

Run: `cd backend && python manage.py test accounts.tests.PermissionTests --verbosity=2`
Expected: All 4 tests PASS.

**Step 6: Commit**

```bash
git add backend/accounts/permissions.py backend/accounts/decorators.py backend/accounts/tests.py
git commit -m "feat: add RBAC permission classes and role_required decorator"
```

---

### Task 5: Auth hook middleware

**Files:**
- Create: `backend/accounts/middleware.py`
- Create: `backend/accounts/hooks.py`
- Modify: `backend/accounts/tests.py` (add middleware tests)
- Modify: `backend/config/settings/base.py` (add middleware + AUTH_HOOKS)

**Step 1: Write failing test**

Add to `backend/accounts/tests.py`:

```python
from django.test import RequestFactory, TestCase, override_settings


class AuthHookMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="mwuser", email="mw@test.com", password="testpass123",
        )

    def test_hooks_called_in_order(self):
        """Verify pre_authenticate and post_authenticate are called."""
        from accounts.middleware import AuthHookMiddleware

        call_log = []

        class TestHook:
            def pre_authenticate(self, request):
                call_log.append("pre")

            def post_authenticate(self, request):
                call_log.append("post")

            def on_response(self, request, response):
                call_log.append("response")

        def get_response(request):
            from django.http import HttpResponse
            return HttpResponse("ok")

        middleware = AuthHookMiddleware(get_response)
        middleware._hooks = [TestHook()]

        request = self.factory.get("/")
        request.user = self.user
        response = middleware(request)

        self.assertEqual(call_log, ["pre", "post", "response"])

    def test_pre_authenticate_can_short_circuit(self):
        """If pre_authenticate returns a response, skip the view."""
        from accounts.middleware import AuthHookMiddleware

        class BlockingHook:
            def pre_authenticate(self, request):
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden("blocked")

        def get_response(request):
            from django.http import HttpResponse
            return HttpResponse("ok")

        middleware = AuthHookMiddleware(get_response)
        middleware._hooks = [BlockingHook()]

        request = self.factory.get("/")
        request.user = self.user
        response = middleware(request)

        self.assertEqual(response.status_code, 403)
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test accounts.tests.AuthHookMiddlewareTests --verbosity=2`
Expected: FAIL — middleware module doesn't exist.

**Step 3: Implement middleware and hooks**

Create `backend/accounts/middleware.py`:

```python
from django.conf import settings
from django.utils.module_loading import import_string


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
```

Create `backend/accounts/hooks.py`:

```python
import logging

logger = logging.getLogger(__name__)


class AuditLogHook:
    """Logs authentication events."""

    def post_authenticate(self, request):
        if hasattr(request, "user") and request.user.is_authenticated:
            logger.info(
                "auth.access user=%s path=%s method=%s",
                request.user.username,
                request.path,
                request.method,
            )
```

**Step 4: Add middleware to settings**

In `backend/config/settings/base.py`, add after the `"django_htmx.middleware.HtmxMiddleware"` line in MIDDLEWARE:

```python
    "accounts.middleware.AuthHookMiddleware",
```

Add at the end of the file:

```python
# Auth hook classes — loaded by AuthHookMiddleware
AUTH_HOOKS = []
```

**Step 5: Run tests to verify they pass**

Run: `cd backend && python manage.py test accounts.tests.AuthHookMiddlewareTests --verbosity=2`
Expected: All 2 tests PASS.

**Step 6: Commit**

```bash
git add backend/accounts/middleware.py backend/accounts/hooks.py backend/accounts/tests.py backend/config/settings/base.py
git commit -m "feat: add pluggable AuthHookMiddleware with audit log hook"
```

---

### Task 6: Configure allauth, simplejwt, and dj-rest-auth in settings

**Files:**
- Modify: `backend/config/settings/base.py`

**Step 1: Update INSTALLED_APPS in base.py**

Add after the `"django_htmx"` line in the third-party section:

```python
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "dj_rest_auth",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
```

**Step 2: Add allauth middleware**

Add after `"accounts.middleware.AuthHookMiddleware"` in MIDDLEWARE:

```python
    "allauth.account.middleware.AccountMiddleware",
```

**Step 3: Add allauth context processor**

Not needed — `"django.template.context_processors.request"` is already present, which allauth requires.

**Step 4: Add configuration blocks at end of base.py**

```python
# django.contrib.sites
SITE_ID = 1

# django-allauth
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_ADAPTER = "accounts.adapters.AccountAdapter"
LOGIN_REDIRECT_URL = "/"
LOGIN_URL = "/accounts/login/"

# allauth MFA / WebAuthn
MFA_SUPPORTED_TYPES = ["recovery_codes", "totp", "webauthn"]
MFA_PASSKEY_LOGIN_ENABLED = True
MFA_PASSKEY_SIGNUP_ENABLED = False
MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN = False  # Override to True in development.py

# Django REST Framework — add auth classes
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# djangorestframework-simplejwt
from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# dj-rest-auth
REST_AUTH = {
    "USE_JWT": True,
    "JWT_AUTH_HTTPONLY": True,
}
```

**Note:** This replaces the existing REST_FRAMEWORK dict (lines 86-94) — be careful to replace, not duplicate.

**Step 5: Update development.py**

In `backend/config/settings/development.py`, add:

```python
MFA_WEBAUTHN_ALLOW_INSECURE_ORIGIN = True
```

**Step 6: Create the adapter**

Create `backend/accounts/adapters.py`:

```python
from allauth.account.adapter import DefaultAccountAdapter

from .models import User


class AccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        # First user ever gets admin role
        if not User.objects.exists():
            user.role = User.Role.ADMIN
        if commit:
            user.save()
        return user
```

**Step 7: Run migrations**

Run: `cd backend && python manage.py migrate`
Expected: allauth, sites, token_blacklist migrations apply cleanly.

**Step 8: Verify the server starts**

Run: `cd backend && python manage.py check`
Expected: System check identified no issues.

**Step 9: Commit**

```bash
git add backend/config/settings/base.py backend/config/settings/development.py backend/accounts/adapters.py
git commit -m "feat: configure allauth, simplejwt, dj-rest-auth settings"
```

---

### Task 7: Context processor and URL routing

**Files:**
- Create: `backend/accounts/context_processors.py`
- Create: `backend/accounts/urls.py`
- Create: `backend/accounts/urls_html.py`
- Modify: `backend/config/urls.py`
- Modify: `backend/config/settings/base.py` (add context processor)

**Step 1: Create context processor**

Create `backend/accounts/context_processors.py`:

```python
def user_role(request):
    """Expose user role to all templates."""
    if hasattr(request, "user") and request.user.is_authenticated:
        return {"user_role": request.user.role}
    return {"user_role": None}
```

**Step 2: Register context processor in settings**

In `backend/config/settings/base.py`, add to the context_processors list (after `django.contrib.messages.context_processors.messages`):

```python
                "accounts.context_processors.user_role",
```

**Step 3: Create API auth URLs**

Create `backend/accounts/urls.py`:

```python
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("auth/", include("dj_rest_auth.urls")),
    path("auth/register/", include("dj_rest_auth.registration.urls")),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
```

**Step 4: Create HTML account URLs (placeholder — views built in Task 10)**

Create `backend/accounts/urls_html.py`:

```python
from django.urls import path

urlpatterns = [
    # Profile and user management views added in Task 10
]
```

**Step 5: Update root URL config**

Modify `backend/config/urls.py` to:

```python
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Authentication (allauth HTML views)
    path("accounts/", include("allauth.urls")),
    path("accounts/", include("accounts.urls_html")),
    # DRF API
    path("api/v1/", include("accounts.urls")),
    path("api/v1/", include("devices.urls")),
    path("api/v1/", include("rules.urls")),
    path("api/v1/", include("audits.urls")),
    # HTML views
    path("", include("audits.urls_html")),
    path("devices/", include("devices.urls_html")),
    path("rules/", include("rules.urls_html")),
    path("schedules/", include("audits.urls_html_schedules")),
]
```

**Step 6: Verify server starts**

Run: `cd backend && python manage.py check`
Expected: No issues.

**Step 7: Commit**

```bash
git add backend/accounts/context_processors.py backend/accounts/urls.py backend/accounts/urls_html.py backend/config/urls.py backend/config/settings/base.py
git commit -m "feat: add auth URL routing and user_role context processor"
```

---

### Task 8: Protect existing DRF API views with permission classes

**Files:**
- Modify: `backend/devices/views.py`
- Modify: `backend/rules/views.py`
- Modify: `backend/audits/views.py`
- Modify: `backend/accounts/tests.py` (add API auth tests)

**Step 1: Write failing test**

Add to `backend/accounts/tests.py`:

```python
from rest_framework.test import APITestCase as DRFAPITestCase


class APIAuthTests(DRFAPITestCase):
    def test_unauthenticated_devices_returns_401(self):
        response = self.client.get("/api/v1/devices/")
        self.assertEqual(response.status_code, 401)

    def test_viewer_can_read_devices(self):
        viewer = User.objects.create_user(
            username="apiviewer", email="apiviewer@test.com", password="testpass123",
            role="viewer",
        )
        self.client.force_authenticate(user=viewer)
        response = self.client.get("/api/v1/devices/")
        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_create_device(self):
        viewer = User.objects.create_user(
            username="apiv2", email="apiv2@test.com", password="testpass123",
            role="viewer",
        )
        self.client.force_authenticate(user=viewer)
        response = self.client.post("/api/v1/devices/", {
            "name": "test-device",
            "hostname": "test.local",
            "api_endpoint": "https://test.local/api",
        })
        self.assertEqual(response.status_code, 403)

    def test_editor_can_create_device(self):
        editor = User.objects.create_user(
            username="apied", email="apied@test.com", password="testpass123",
            role="editor",
        )
        self.client.force_authenticate(user=editor)
        response = self.client.post("/api/v1/devices/", {
            "name": "test-device",
            "hostname": "test.local",
            "api_endpoint": "https://test.local/api",
        })
        self.assertEqual(response.status_code, 201)
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test accounts.tests.APIAuthTests --verbosity=2`
Expected: FAIL — default permission is now IsAuthenticated (from Task 6), but ViewSets don't have role-based restrictions yet. The 401 test should pass, but create tests won't enforce roles.

**Step 3: Add permissions to devices/views.py**

Modify `backend/devices/views.py`:

```python
import requests
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsEditorOrAbove, IsViewerOrAbove

from .models import Device
from .serializers import DeviceSerializer


class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.prefetch_related("headers").all()
    serializer_class = DeviceSerializer
    filterset_fields = ["enabled"]
    search_fields = ["name", "hostname"]
    ordering_fields = ["name", "created_at"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]

    @action(detail=True, methods=["post"])
    def test_connection(self, request, pk=None):
        device = self.get_object()
        headers = {h.key: h.value for h in device.headers.all()}
        try:
            response = requests.get(
                device.api_endpoint,
                headers=headers,
                timeout=10,
            )
            return Response(
                {
                    "success": True,
                    "status_code": response.status_code,
                    "content_length": len(response.content),
                }
            )
        except requests.RequestException as exc:
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
```

**Step 4: Add permissions to rules/views.py**

Modify `backend/rules/views.py`:

```python
import ast

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsEditorOrAbove, IsViewerOrAbove

from .models import CustomRule, SimpleRule
from .serializers import CustomRuleSerializer, SimpleRuleSerializer


class SimpleRuleViewSet(viewsets.ModelViewSet):
    queryset = SimpleRule.objects.all()
    serializer_class = SimpleRuleSerializer
    filterset_fields = ["device", "enabled", "severity", "rule_type"]
    search_fields = ["name", "description", "pattern"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]


class CustomRuleViewSet(viewsets.ModelViewSet):
    queryset = CustomRule.objects.all()
    serializer_class = CustomRuleSerializer
    filterset_fields = ["device", "enabled", "severity"]
    search_fields = ["name", "description", "filename"]

    def get_permissions(self):
        if self.action in ("list", "retrieve", "validate"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]

    @action(detail=True, methods=["post"])
    def validate(self, request, pk=None):
        rule = self.get_object()
        try:
            ast.parse(rule.content)
            return Response({"valid": True})
        except SyntaxError as exc:
            return Response({"valid": False, "error": str(exc)})
```

**Step 5: Add permissions to audits/views.py**

Modify `backend/audits/views.py` — add imports and `get_permissions` to each ViewSet:

Add import at top:

```python
from accounts.permissions import IsEditorOrAbove, IsViewerOrAbove
```

Add to `AuditRunViewSet`:

```python
    def get_permissions(self):
        if self.action in ("list", "retrieve", "results", "config"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]
```

Add to `AuditScheduleViewSet`:

```python
    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]
```

`DashboardSummaryView` — add:

```python
    permission_classes = [IsViewerOrAbove]
```

**Step 6: Run tests to verify they pass**

Run: `cd backend && python manage.py test accounts.tests.APIAuthTests --verbosity=2`
Expected: All 4 tests PASS.

**Step 7: Run all existing tests to check for regressions**

Run: `cd backend && python manage.py test --verbosity=2`
Expected: Existing tests may fail because they now require authentication. Fix by adding `force_authenticate` or creating users in existing test setups. Address these failures before committing.

**Fixing existing test regressions:** In test files that use `APITestCase`, you'll need to create a user and call `self.client.force_authenticate(user=user)` in `setUp`. For HTML view tests using `TestCase`, use `self.client.login(username=..., password=...)`. Create users with `role="admin"` so existing tests have full permissions.

**Step 8: Commit**

```bash
git add backend/devices/views.py backend/rules/views.py backend/audits/views.py backend/accounts/tests.py
git commit -m "feat: add role-based permissions to all DRF API views"
```

---

### Task 9: Protect existing HTML views with login and role requirements

**Files:**
- Modify: `backend/devices/views_html.py`
- Modify: `backend/audits/views_html.py`
- Modify: `backend/config/settings/base.py` (add LOGIN_URL if not set)

**Step 1: Write a failing test**

Add to `backend/accounts/tests.py`:

```python
class HTMLAuthTests(TestCase):
    def test_unauthenticated_redirect_to_login(self):
        response = self.client.get("/devices/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_viewer_can_access_device_list(self):
        user = User.objects.create_user(
            username="htmlviewer", email="hv@test.com", password="testpass123",
            role="viewer",
        )
        self.client.login(username="htmlviewer", password="testpass123")
        response = self.client.get("/devices/")
        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_delete_device(self):
        from devices.models import Device
        device = Device.objects.create(
            name="del-test", hostname="h.local",
            api_endpoint="https://h.local/api",
        )
        user = User.objects.create_user(
            username="htmlv2", email="hv2@test.com", password="testpass123",
            role="viewer",
        )
        self.client.login(username="htmlv2", password="testpass123")
        response = self.client.post(f"/devices/{device.pk}/delete/")
        self.assertEqual(response.status_code, 403)
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python manage.py test accounts.tests.HTMLAuthTests --verbosity=2`
Expected: FAIL — views not protected yet.

**Step 3: Protect devices/views_html.py**

Add imports at top of `backend/devices/views_html.py`:

```python
from django.contrib.auth.mixins import LoginRequiredMixin

from accounts.decorators import RoleRequiredMixin, role_required
```

Update class-based views to use mixins. The mixin order matters — `RoleRequiredMixin` (or `LoginRequiredMixin`) must come before the Django generic view:

- `DeviceListView` → add `LoginRequiredMixin` as first parent (viewers can see)
- `DeviceCreateView` → add `RoleRequiredMixin` with `min_role = "editor"` as first parent
- `DeviceUpdateView` → add `RoleRequiredMixin` with `min_role = "editor"` as first parent
- `DeviceDetailView` → add `LoginRequiredMixin` as first parent

For function views, wrap with decorators:

- `device_delete` → add `@role_required("editor")` above `@require_POST`
- `device_test_connection` → add `@role_required("editor")` above `@require_POST`
- `device_run_audit` → add `@role_required("editor")` above `@require_POST`
- `device_header_add` → add `@role_required("editor")` (no `@require_POST` needed, already GET)

Example for `DeviceListView`:

```python
class DeviceListView(LoginRequiredMixin, generic.ListView):
```

Example for `DeviceCreateView`:

```python
class DeviceCreateView(RoleRequiredMixin, generic.CreateView):
    min_role = "editor"
```

Example for `device_delete`:

```python
@role_required("editor")
@require_POST
def device_delete(request, pk):
```

**Step 4: Protect audits/views_html.py**

Same pattern. Add imports and mixins/decorators:

- `DashboardView` → `LoginRequiredMixin`
- `AuditRunListView` → `LoginRequiredMixin`
- `AuditRunDetailView` → `LoginRequiredMixin`
- `ScheduleListView` → `LoginRequiredMixin`
- `ScheduleCreateView` → `RoleRequiredMixin` with `min_role = "editor"`
- `ScheduleUpdateView` → `RoleRequiredMixin` with `min_role = "editor"`
- `audit_run_status_fragment` → `@role_required("viewer")` (login check)
- `audit_run_config` → `@role_required("viewer")`
- `schedule_delete` → `@role_required("editor")`

**Note:** Also protect the rules HTML views (`backend/rules/views_html.py` if it exists) with the same pattern. Use `Glob` to find it, then apply the same pattern.

**Step 5: Run tests to verify they pass**

Run: `cd backend && python manage.py test accounts.tests.HTMLAuthTests --verbosity=2`
Expected: All 3 tests PASS.

**Step 6: Run all tests**

Run: `cd backend && python manage.py test --verbosity=2`
Expected: May need to fix existing HTML view tests by logging in first. Add `self.client.login()` calls to existing test setups.

**Step 7: Commit**

```bash
git add backend/devices/views_html.py backend/audits/views_html.py backend/accounts/tests.py
git commit -m "feat: protect all HTML views with login and role requirements"
```

---

### Task 10: User profile and user management views

**Files:**
- Create: `backend/accounts/serializers.py`
- Create: `backend/accounts/forms.py`
- Create: `backend/accounts/views_html.py`
- Modify: `backend/accounts/urls_html.py`

**Step 1: Create user serializer for API**

Create `backend/accounts/serializers.py`:

```python
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "role", "is_api_enabled", "date_joined")
        read_only_fields = ("id", "date_joined")
```

**Step 2: Create profile and user management forms**

Create `backend/accounts/forms.py`:

```python
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")


class UserRoleForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("role", "is_active", "is_api_enabled")
```

**Step 3: Create HTML views**

Create `backend/accounts/views_html.py`:

```python
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
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
```

**Step 4: Update HTML URLs**

Replace `backend/accounts/urls_html.py`:

```python
from django.urls import path

from . import views_html

urlpatterns = [
    path("profile/", views_html.ProfileView.as_view(), name="profile"),
    path("users/", views_html.UserListView.as_view(), name="user-list"),
    path(
        "users/<int:pk>/edit/",
        views_html.UserUpdateRoleView.as_view(),
        name="user-edit",
    ),
]
```

**Step 5: Run check**

Run: `cd backend && python manage.py check`
Expected: No issues.

**Step 6: Commit**

```bash
git add backend/accounts/serializers.py backend/accounts/forms.py backend/accounts/views_html.py backend/accounts/urls_html.py
git commit -m "feat: add user profile and admin user management views"
```

---

### Task 11: allauth template overrides (login, signup, base)

**Files:**
- Create: `backend/templates/account/login.html`
- Create: `backend/templates/account/signup.html`
- Create: `backend/templates/account/logout.html`
- Create: `backend/templates/account/password_reset.html`
- Create: `backend/templates/accounts/profile.html`
- Create: `backend/templates/accounts/user_list.html`
- Create: `backend/templates/accounts/user_edit.html`
- Modify: `backend/templates/partials/sidebar.html`

**Step 1: Create allauth login template**

Create `backend/templates/account/login.html`:

```html
{% extends "base.html" %}
{% block title %}Login — Netaudit{% endblock %}
{% block content %}
<div class="auth-container">
    <h2>Login</h2>
    <form method="post" action="{% url 'account_login' %}">
        {% csrf_token %}
        {{ form.as_p }}
        <button type="submit" class="btn btn-primary">Sign In</button>
    </form>
    {% if passkey_login_enabled %}
    <div class="passkey-login">
        <p>Or sign in with a passkey:</p>
        <button id="passkey-login-btn" class="btn btn-secondary"
                hx-post="{% url 'mfa_login_webauthn' %}"
                hx-target=".auth-container">
            Sign in with Passkey
        </button>
    </div>
    {% endif %}
    <p><a href="{% url 'account_signup' %}">Create an account</a></p>
    <p><a href="{% url 'account_reset_password' %}">Forgot password?</a></p>
</div>
{% endblock %}
```

**Step 2: Create allauth signup template**

Create `backend/templates/account/signup.html`:

```html
{% extends "base.html" %}
{% block title %}Register — Netaudit{% endblock %}
{% block content %}
<div class="auth-container">
    <h2>Create Account</h2>
    <form method="post" action="{% url 'account_signup' %}">
        {% csrf_token %}
        {{ form.as_p }}
        <button type="submit" class="btn btn-primary">Register</button>
    </form>
    <p><a href="{% url 'account_login' %}">Already have an account? Sign in</a></p>
</div>
{% endblock %}
```

**Step 3: Create logout template**

Create `backend/templates/account/logout.html`:

```html
{% extends "base.html" %}
{% block title %}Logout — Netaudit{% endblock %}
{% block content %}
<div class="auth-container">
    <h2>Sign Out</h2>
    <p>Are you sure you want to sign out?</p>
    <form method="post" action="{% url 'account_logout' %}">
        {% csrf_token %}
        <button type="submit" class="btn btn-primary">Sign Out</button>
    </form>
</div>
{% endblock %}
```

**Step 4: Create password reset template**

Create `backend/templates/account/password_reset.html`:

```html
{% extends "base.html" %}
{% block title %}Reset Password — Netaudit{% endblock %}
{% block content %}
<div class="auth-container">
    <h2>Reset Password</h2>
    <form method="post" action="{% url 'account_reset_password' %}">
        {% csrf_token %}
        {{ form.as_p }}
        <button type="submit" class="btn btn-primary">Send Reset Email</button>
    </form>
    <p><a href="{% url 'account_login' %}">Back to login</a></p>
</div>
{% endblock %}
```

**Step 5: Create profile template**

Create `backend/templates/accounts/profile.html`:

```html
{% extends "base.html" %}
{% load badge_tags %}
{% block title %}Profile — Netaudit{% endblock %}
{% block content %}
<div class="page-header">
    <h2>Profile</h2>
    <span>{{ user.role|badge }}</span>
</div>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit" class="btn btn-primary">Save</button>
</form>
<div class="profile-section">
    <h3>Security</h3>
    <ul>
        <li><a href="{% url 'mfa_index' %}">Manage passkeys &amp; MFA</a></li>
        <li><a href="{% url 'account_change_password' %}">Change password</a></li>
    </ul>
</div>
{% endblock %}
```

**Step 6: Create user list template (admin)**

Create `backend/templates/accounts/user_list.html`:

```html
{% extends "base.html" %}
{% load badge_tags %}
{% block title %}Users — Netaudit{% endblock %}
{% block content %}
<div class="page-header">
    <h2>Users</h2>
</div>
<table class="table">
    <thead>
        <tr>
            <th>Username</th>
            <th>Email</th>
            <th>Role</th>
            <th>Active</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        {% for u in users %}
        <tr>
            <td>{{ u.username }}</td>
            <td>{{ u.email }}</td>
            <td>{{ u.role|badge }}</td>
            <td>{{ u.is_active|enabled_badge }}</td>
            <td><a href="{% url 'user-edit' u.pk %}" class="btn btn-sm">Edit</a></td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endblock %}
```

**Step 7: Create user edit template (admin)**

Create `backend/templates/accounts/user_edit.html`:

```html
{% extends "base.html" %}
{% block title %}Edit User — Netaudit{% endblock %}
{% block content %}
<div class="page-header">
    <h2>Edit User: {{ target_user.username }}</h2>
</div>
<form method="post">
    {% csrf_token %}
    {{ form.as_p }}
    <button type="submit" class="btn btn-primary">Save</button>
    <a href="{% url 'user-list' %}" class="btn btn-secondary">Cancel</a>
</form>
{% endblock %}
```

**Step 8: Update sidebar**

Replace `backend/templates/partials/sidebar.html`:

```html
{% load nav_tags badge_tags %}
<nav class="sidebar">
    <div class="sidebar-header">
        <h1>Netaudit</h1>
    </div>
    <ul class="sidebar-nav">
        <li><a href="{% url 'dashboard' %}" class="{% active_class request '/' exact=True %}">Dashboard</a></li>
        <li><a href="{% url 'device-list-html' %}" class="{% active_class request '/devices/' %}">Devices</a></li>
        <li><a href="{% url 'simplerule-list-html' %}" class="{% active_class request '/rules/simple/' %}">Simple Rules</a></li>
        <li><a href="{% url 'customrule-list-html' %}" class="{% active_class request '/rules/custom/' %}">Custom Rules</a></li>
        <li><a href="{% url 'auditrun-list-html' %}" class="{% active_class request '/audits/' %}">Audits</a></li>
        <li><a href="{% url 'schedule-list-html' %}" class="{% active_class request '/schedules/' %}">Schedules</a></li>
        {% if user_role == "admin" %}
        <li><a href="{% url 'user-list' %}" class="{% active_class request '/accounts/users/' %}">Users</a></li>
        {% endif %}
    </ul>
    {% if user.is_authenticated %}
    <div class="sidebar-footer">
        <div class="sidebar-user">
            <span class="sidebar-username">{{ user.username }}</span>
            {{ user.role|badge }}
        </div>
        <ul class="sidebar-nav">
            <li><a href="{% url 'profile' %}">Profile</a></li>
            <li>
                <form method="post" action="{% url 'account_logout' %}">
                    {% csrf_token %}
                    <button type="submit" class="sidebar-logout-btn">Logout</button>
                </form>
            </li>
        </ul>
    </div>
    {% endif %}
</nav>
```

**Step 9: Verify server starts and login page renders**

Run: `cd backend && python manage.py check`
Expected: No issues.

Run: `cd backend && python manage.py runserver 0.0.0.0:8000 &` then test login page loads.

**Step 10: Commit**

```bash
git add backend/templates/
git commit -m "feat: add auth templates (login, signup, profile, user management, sidebar)"
```

---

### Task 12: Fix existing test suites for auth requirements

**Files:**
- Modify: `backend/devices/tests.py`
- Modify: `backend/rules/tests.py`
- Modify: `backend/audits/tests.py`
- Modify: `backend/audits/test_services.py`

**Step 1: Run all existing tests**

Run: `cd backend && python manage.py test --verbosity=2 2>&1 | tail -40`
Expected: Some tests fail with 401/302 because views now require auth.

**Step 2: Fix each test file**

The pattern for each test file:

For `APITestCase` subclasses, add to `setUp`:

```python
from django.contrib.auth import get_user_model
User = get_user_model()

def setUp(self):
    self.user = User.objects.create_user(
        username="testuser", email="test@test.com", password="testpass123",
        role="admin",
    )
    self.client.force_authenticate(user=self.user)
```

For `TestCase` subclasses that test HTML views, add to `setUp`:

```python
from django.contrib.auth import get_user_model
User = get_user_model()

def setUp(self):
    self.user = User.objects.create_user(
        username="testuser", email="test@test.com", password="testpass123",
        role="admin",
    )
    self.client.login(username="testuser", password="testpass123")
```

Go through each test file (`devices/tests.py`, `rules/tests.py`, `audits/tests.py`, `audits/test_services.py`), find test classes that make HTTP requests, and add authentication to their setUp methods.

**Step 3: Run all tests and iterate until green**

Run: `cd backend && python manage.py test --verbosity=2`
Expected: All tests PASS.

**Step 4: Commit**

```bash
git add backend/devices/tests.py backend/rules/tests.py backend/audits/tests.py backend/audits/test_services.py
git commit -m "fix: update existing tests to authenticate before making requests"
```

---

### Task 13: End-to-end auth flow tests

**Files:**
- Modify: `backend/accounts/tests.py`

**Step 1: Add registration flow test**

Add to `backend/accounts/tests.py`:

```python
class AuthFlowTests(TestCase):
    def test_registration_creates_viewer_by_default(self):
        response = self.client.post("/accounts/signup/", {
            "username": "newuser",
            "email": "new@test.com",
            "password1": "complexpass123!",
            "password2": "complexpass123!",
        })
        user = User.objects.get(username="newuser")
        self.assertEqual(user.role, "viewer")

    def test_first_user_gets_admin_role(self):
        # Clear all users first
        User.objects.all().delete()
        response = self.client.post("/accounts/signup/", {
            "username": "firstuser",
            "email": "first@test.com",
            "password1": "complexpass123!",
            "password2": "complexpass123!",
        })
        user = User.objects.get(username="firstuser")
        self.assertEqual(user.role, "admin")

    def test_login_logout_flow(self):
        User.objects.create_user(
            username="flowuser", email="flow@test.com", password="testpass123",
        )
        # Login
        response = self.client.post("/accounts/login/", {
            "login": "flowuser",
            "password": "testpass123",
        })
        self.assertEqual(response.status_code, 302)  # Redirect on success

        # Access protected page
        response = self.client.get("/devices/")
        self.assertEqual(response.status_code, 200)

        # Logout
        response = self.client.post("/accounts/logout/")
        self.assertEqual(response.status_code, 302)

        # Protected page redirects to login
        response = self.client.get("/devices/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)


class JWTAuthTests(DRFAPITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="jwtuser", email="jwt@test.com", password="testpass123",
            role="editor",
        )

    def test_obtain_jwt_token(self):
        response = self.client.post("/api/v1/auth/login/", {
            "username": "jwtuser",
            "password": "testpass123",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_access_api_with_jwt(self):
        # Get token
        response = self.client.post("/api/v1/auth/login/", {
            "username": "jwtuser",
            "password": "testpass123",
        })
        token = response.data["access"]
        # Use token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/api/v1/devices/")
        self.assertEqual(response.status_code, 200)

    def test_invalid_token_returns_401(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")
        response = self.client.get("/api/v1/devices/")
        self.assertEqual(response.status_code, 401)
```

**Step 2: Run the auth flow tests**

Run: `cd backend && python manage.py test accounts.tests.AuthFlowTests accounts.tests.JWTAuthTests --verbosity=2`
Expected: All tests PASS. If any fail, debug and fix the allauth/dj-rest-auth configuration.

**Step 3: Run full test suite**

Run: `cd backend && python manage.py test --verbosity=2`
Expected: All tests PASS.

**Step 4: Commit**

```bash
git add backend/accounts/tests.py
git commit -m "test: add end-to-end auth flow and JWT tests"
```

---

### Task 14: Final verification and cleanup

**Step 1: Run full test suite**

Run: `cd backend && python manage.py test --verbosity=2`
Expected: All tests PASS.

**Step 2: Run Django system checks**

Run: `cd backend && python manage.py check --deploy 2>&1 | head -20`
Expected: No critical issues. Some warnings about HTTPS settings are expected in dev.

**Step 3: Verify the server starts and key flows work**

Run: `cd backend && python manage.py runserver 0.0.0.0:8000`

Manual verification:
- Visit `http://localhost:8000/` — should redirect to login
- Register a new user — should get admin role (first user)
- Login — should see dashboard with sidebar showing username/role
- Visit `/accounts/profile/` — should show profile form
- Visit `/accounts/users/` — should show user list (admin only)
- API: `curl -X POST http://localhost:8000/api/v1/auth/login/ -d '{"username":"...","password":"..."}' -H 'Content-Type: application/json'` — should return JWT tokens
- API: Use token to access `/api/v1/devices/`

**Step 4: Final commit**

If any fixes were needed during verification:

```bash
git add -A
git commit -m "fix: address issues found during final verification"
```

---

## Task Summary

| Task | Description | Key Files |
|------|-------------|-----------|
| 1 | Install dependencies | `requirements.txt` |
| 2 | Custom User model + accounts app | `accounts/models.py`, `base.py` |
| 3 | Role-to-group sync signal | `accounts/signals.py` |
| 4 | Permission classes + decorator | `accounts/permissions.py`, `accounts/decorators.py` |
| 5 | Auth hook middleware | `accounts/middleware.py`, `accounts/hooks.py` |
| 6 | Configure allauth + simplejwt + dj-rest-auth | `base.py`, `accounts/adapters.py` |
| 7 | Context processor + URL routing | `accounts/urls.py`, `config/urls.py` |
| 8 | Protect DRF API views | `devices/views.py`, `rules/views.py`, `audits/views.py` |
| 9 | Protect HTML views | `devices/views_html.py`, `audits/views_html.py` |
| 10 | Profile + user management views | `accounts/views_html.py`, `accounts/forms.py` |
| 11 | Templates (login, signup, sidebar) | `templates/account/`, `templates/accounts/`, `sidebar.html` |
| 12 | Fix existing tests for auth | `devices/tests.py`, `rules/tests.py`, `audits/tests.py` |
| 13 | End-to-end auth flow tests | `accounts/tests.py` |
| 14 | Final verification | — |
