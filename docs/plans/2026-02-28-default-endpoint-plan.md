# Default API Endpoint Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a configurable default API endpoint so devices without a custom endpoint automatically use `<default_endpoint>/<device_name>`.

**Architecture:** New `settings` Django app with a singleton `SiteSettings` model. A Settings page in the web UI lets users configure the default endpoint. The `_fetch_config()` function and all test-connection views resolve the effective endpoint at runtime.

**Tech Stack:** Django, Django REST Framework, HTMX, Django templates

---

### Task 1: Create the `settings` Django App and SiteSettings Model

**Files:**
- Create: `backend/settings/__init__.py`
- Create: `backend/settings/apps.py`
- Create: `backend/settings/models.py`
- Create: `backend/settings/admin.py`
- Create: `backend/settings/migrations/__init__.py`
- Modify: `backend/config/settings/base.py:15-33` (add to INSTALLED_APPS)

**Step 1: Create the app files**

Create `backend/settings/apps.py`:
```python
from django.apps import AppConfig


class SiteSettingsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "settings"
    label = "site_settings"
    verbose_name = "Site Settings"
```

Create `backend/settings/__init__.py`: empty file.

Create `backend/settings/migrations/__init__.py`: empty file.

Create `backend/settings/models.py`:
```python
from django.db import models


class SiteSettings(models.Model):
    default_api_endpoint = models.URLField(
        blank=True,
        default="",
        help_text="Base URL for devices without a custom endpoint. "
        "Effective URL: <this>/<device_name>",
    )

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"

    def __str__(self):
        return "Site Settings"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
```

Create `backend/settings/admin.py`:
```python
from django.contrib import admin

from .models import SiteSettings

admin.site.register(SiteSettings)
```

**Step 2: Register the app in INSTALLED_APPS**

In `backend/config/settings/base.py`, add `"settings"` to the `# Local apps` section:
```python
    # Local apps
    "devices",
    "rules",
    "audits",
    "common",
    "settings",
```

**Step 3: Create and run the migration**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py makemigrations site_settings`
Expected: Migration file created.

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py migrate`
Expected: Migration applied successfully.

**Step 4: Write tests for SiteSettings model**

Create `backend/settings/tests.py`:
```python
from django.test import TestCase

from .models import SiteSettings


class SiteSettingsModelTests(TestCase):

    def test_load_creates_singleton(self):
        self.assertEqual(SiteSettings.objects.count(), 0)
        settings = SiteSettings.load()
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(settings.pk, 1)

    def test_load_returns_existing(self):
        SiteSettings.objects.create(
            pk=1, default_api_endpoint="https://example.com/api"
        )
        settings = SiteSettings.load()
        self.assertEqual(settings.default_api_endpoint, "https://example.com/api")
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_save_forces_pk_1(self):
        settings = SiteSettings(pk=99, default_api_endpoint="https://test.com")
        settings.save()
        self.assertEqual(settings.pk, 1)
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_default_api_endpoint_blank_by_default(self):
        settings = SiteSettings.load()
        self.assertEqual(settings.default_api_endpoint, "")

    def test_str(self):
        settings = SiteSettings.load()
        self.assertEqual(str(settings), "Site Settings")
```

**Step 5: Run tests to verify**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py test settings --verbosity=2`
Expected: All 5 tests PASS.

**Step 6: Commit**

```bash
git add backend/settings/ backend/config/settings/base.py
git commit -m "feat: add SiteSettings singleton model for default API endpoint"
```

---

### Task 2: Make Device.api_endpoint Optional

**Files:**
- Modify: `backend/devices/models.py:7`
- Create migration

**Step 1: Write the failing test**

Add to `backend/devices/tests.py` in `DeviceModelTests`:
```python
    def test_create_device_without_api_endpoint(self):
        device = Device.objects.create(
            name="no-endpoint",
            hostname="no-endpoint.local",
        )
        self.assertEqual(device.api_endpoint, "")
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py test devices.tests.DeviceModelTests.test_create_device_without_api_endpoint --verbosity=2`
Expected: FAIL (IntegrityError or validation error — api_endpoint is currently required)

**Step 3: Make api_endpoint optional**

In `backend/devices/models.py`, change line 7:
```python
    api_endpoint = models.URLField(blank=True, default="")
```

**Step 4: Create and run migration**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py makemigrations devices`
Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py migrate`

**Step 5: Run test to verify it passes**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py test devices.tests.DeviceModelTests.test_create_device_without_api_endpoint --verbosity=2`
Expected: PASS

**Step 6: Run all existing device tests to check for regressions**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py test devices --verbosity=2`
Expected: All tests PASS. The existing tests explicitly set api_endpoint so they won't break.

**Step 7: Commit**

```bash
git add backend/devices/models.py backend/devices/migrations/ backend/devices/tests.py
git commit -m "feat: make Device.api_endpoint optional to support default endpoint"
```

---

### Task 3: Add `effective_api_endpoint` Property to Device Model

**Files:**
- Modify: `backend/devices/models.py`
- Modify: `backend/devices/tests.py`

**Step 1: Write failing tests**

Add to `backend/devices/tests.py` in `DeviceModelTests`:
```python
    def test_effective_api_endpoint_uses_own_endpoint(self):
        device = Device.objects.create(
            name="custom-ep",
            hostname="custom.local",
            api_endpoint="https://custom.local/api",
        )
        self.assertEqual(device.effective_api_endpoint, "https://custom.local/api")

    def test_effective_api_endpoint_uses_default_when_blank(self):
        from settings.models import SiteSettings
        site = SiteSettings.load()
        site.default_api_endpoint = "https://default.example.com/api"
        site.save()

        device = Device.objects.create(
            name="switch-99",
            hostname="switch-99.local",
        )
        self.assertEqual(
            device.effective_api_endpoint,
            "https://default.example.com/api/switch-99",
        )

    def test_effective_api_endpoint_strips_trailing_slash(self):
        from settings.models import SiteSettings
        site = SiteSettings.load()
        site.default_api_endpoint = "https://default.example.com/api/"
        site.save()

        device = Device.objects.create(
            name="switch-100",
            hostname="switch-100.local",
        )
        self.assertEqual(
            device.effective_api_endpoint,
            "https://default.example.com/api/switch-100",
        )

    def test_effective_api_endpoint_empty_when_no_config(self):
        device = Device.objects.create(
            name="orphan",
            hostname="orphan.local",
        )
        self.assertEqual(device.effective_api_endpoint, "")
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py test devices.tests.DeviceModelTests.test_effective_api_endpoint_uses_own_endpoint --verbosity=2`
Expected: FAIL (AttributeError — property doesn't exist yet)

**Step 3: Implement the property**

In `backend/devices/models.py`, add after `__str__`:
```python
    @property
    def effective_api_endpoint(self):
        if self.api_endpoint:
            return self.api_endpoint
        from settings.models import SiteSettings
        site = SiteSettings.load()
        if site.default_api_endpoint:
            base = site.default_api_endpoint.rstrip("/")
            return f"{base}/{self.name}"
        return ""
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py test devices.tests.DeviceModelTests -k effective --verbosity=2`
Expected: All 4 new tests PASS.

**Step 5: Commit**

```bash
git add backend/devices/models.py backend/devices/tests.py
git commit -m "feat: add effective_api_endpoint property with default fallback"
```

---

### Task 4: Update `_fetch_config()` and Test Connection Views to Use Effective Endpoint

**Files:**
- Modify: `backend/audits/services.py:197-205`
- Modify: `backend/devices/views.py:17-38`
- Modify: `backend/devices/views_html.py:107-130`

**Step 1: Update `_fetch_config()` in audits/services.py**

Replace lines 197-205:
```python
def _fetch_config(device):
    """
    Retrieve the device configuration via HTTP GET.

    Uses device.effective_api_endpoint which falls back to the
    site-wide default endpoint if the device has no custom endpoint.
    """
    endpoint = device.effective_api_endpoint
    if not endpoint:
        raise ValueError(
            f"Device '{device.name}' has no API endpoint configured "
            "and no default endpoint is set."
        )

    headers = {h.key: h.value for h in device.headers.all()}
    response = requests.get(endpoint, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text
```

**Step 2: Update DRF test_connection view in devices/views.py**

Change `device.api_endpoint` to `device.effective_api_endpoint` on line 22:
```python
    @action(detail=True, methods=["post"])
    def test_connection(self, request, pk=None):
        device = self.get_object()
        endpoint = device.effective_api_endpoint
        if not endpoint:
            return Response(
                {"success": False, "error": "No API endpoint configured and no default endpoint is set."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        headers = {h.key: h.value for h in device.headers.all()}
        try:
            response = requests.get(endpoint, headers=headers, timeout=10)
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

**Step 3: Update HTML test_connection view in devices/views_html.py**

Change `device.api_endpoint` to `device.effective_api_endpoint` on line 112:
```python
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
```

**Step 4: Update existing test assertions**

In `backend/devices/tests.py`, the `test_test_connection_success` test asserts the exact URL called. Update the mock assertion (line 354) — this still works because the device has `api_endpoint` set, so `effective_api_endpoint` returns it as-is. No change needed.

**Step 5: Run all tests**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py test devices audits --verbosity=2`
Expected: All tests PASS.

**Step 6: Commit**

```bash
git add backend/audits/services.py backend/devices/views.py backend/devices/views_html.py
git commit -m "feat: use effective_api_endpoint in config fetch and test connection"
```

---

### Task 5: Update Device Serializer and Form to Handle Optional Endpoint

**Files:**
- Modify: `backend/devices/serializers.py`
- Modify: `backend/devices/forms.py`

**Step 1: Update the DRF serializer**

In `backend/devices/serializers.py`, add `effective_api_endpoint` as a read-only field:
```python
class DeviceSerializer(serializers.ModelSerializer):
    headers = DeviceHeaderSerializer(many=True, required=False)
    effective_api_endpoint = serializers.CharField(read_only=True)

    class Meta:
        model = Device
        fields = [
            "id",
            "name",
            "hostname",
            "api_endpoint",
            "effective_api_endpoint",
            "enabled",
            "headers",
            "created_at",
            "updated_at",
        ]
```

**Step 2: Update the Django form**

In `backend/devices/forms.py`, add help_text to api_endpoint and make it not required:
```python
class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = ["name", "hostname", "api_endpoint", "enabled"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["api_endpoint"].required = False
        self.fields["api_endpoint"].help_text = (
            "Leave blank to use the default endpoint."
        )
```

**Step 3: Run existing tests to check**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py test devices --verbosity=2`
Expected: `test_create_device_missing_required_fields` may now need updating since `api_endpoint` is no longer required in the serializer. Check and update if needed — the test sends only `{"name": "incomplete-device"}` and expects 400. It should still fail because `hostname` is still required.

**Step 4: Commit**

```bash
git add backend/devices/serializers.py backend/devices/forms.py
git commit -m "feat: add effective_api_endpoint to serializer, make form endpoint optional"
```

---

### Task 6: Create Settings Web UI (HTML Views, URLs, Templates)

**Files:**
- Create: `backend/settings/forms.py`
- Create: `backend/settings/views_html.py`
- Create: `backend/settings/urls_html.py`
- Create: `backend/settings/templates/settings/settings_form.html`
- Modify: `backend/config/urls.py`
- Modify: `backend/templates/partials/sidebar.html`

**Step 1: Create the form**

Create `backend/settings/forms.py`:
```python
from django import forms

from .models import SiteSettings


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = ["default_api_endpoint"]
```

**Step 2: Create the view**

Create `backend/settings/views_html.py`:
```python
from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import SiteSettingsForm
from .models import SiteSettings


def settings_view(request):
    site_settings = SiteSettings.load()
    if request.method == "POST":
        form = SiteSettingsForm(request.POST, instance=site_settings)
        if form.is_valid():
            form.save()
            messages.success(request, "Settings saved.")
            return redirect("settings-html")
    else:
        form = SiteSettingsForm(instance=site_settings)
    return render(request, "settings/settings_form.html", {"form": form})
```

**Step 3: Create the URL config**

Create `backend/settings/urls_html.py`:
```python
from django.urls import path

from . import views_html

urlpatterns = [
    path("", views_html.settings_view, name="settings-html"),
]
```

**Step 4: Create the template**

Create directory: `backend/settings/templates/settings/`

Create `backend/settings/templates/settings/settings_form.html`:
```html
{% extends "base.html" %}

{% block title %}Settings — Netaudit{% endblock %}

{% block content %}
<div class="page-header">
    <h2>Settings</h2>
</div>

<form method="post">
    {% csrf_token %}

    <div class="card">
        <h3>Default API Endpoint</h3>
        <p style="color: #999; margin-bottom: 1rem; font-size: 0.9rem;">
            When set, devices without a custom API endpoint will use this base URL
            combined with their name: <code>&lt;default&gt;/&lt;device_name&gt;</code>
        </p>

        <div class="form-group">
            <label for="{{ form.default_api_endpoint.id_for_label }}">Base URL</label>
            {{ form.default_api_endpoint }}
            {% if form.default_api_endpoint.errors %}
            <div class="form-errors">{{ form.default_api_endpoint.errors }}</div>
            {% endif %}
            <span class="helptext">Example: https://network-controller.example.com/api/config</span>
        </div>
    </div>

    <div class="actions">
        <button type="submit" class="btn btn-primary">Save Settings</button>
    </div>
</form>
{% endblock %}
```

**Step 5: Register URLs in config/urls.py**

Add to `backend/config/urls.py`:
```python
    path("settings/", include("settings.urls_html")),
```

**Step 6: Add Settings to sidebar**

In `backend/templates/partials/sidebar.html`, add after the Schedules link:
```html
        <li><a href="{% url 'settings-html' %}" class="{% active_class request '/settings/' %}">Settings</a></li>
```

**Step 7: Run the dev server and manually verify the page loads**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py runserver 0.0.0.0:8000`
Navigate to: `http://localhost:8000/settings/`
Expected: Settings page with Default API Endpoint form.

**Step 8: Commit**

```bash
git add backend/settings/forms.py backend/settings/views_html.py backend/settings/urls_html.py backend/settings/templates/ backend/config/urls.py backend/templates/partials/sidebar.html
git commit -m "feat: add Settings page with default API endpoint configuration"
```

---

### Task 7: Update Device Templates to Show Effective Endpoint

**Files:**
- Modify: `backend/devices/templates/devices/device_detail.html:25-26`
- Modify: `backend/devices/templates/devices/device_list.html:28`
- Modify: `backend/devices/templates/devices/device_form.html:33-38`

**Step 1: Update device detail template**

In `backend/devices/templates/devices/device_detail.html`, replace the API Endpoint display (lines 25-26):
```html
        <dt>API Endpoint</dt>
        <dd>
            {{ device.effective_api_endpoint }}
            {% if not device.api_endpoint and device.effective_api_endpoint %}
                <span class="badge badge-info">default</span>
            {% endif %}
            {% if not device.effective_api_endpoint %}
                <span style="color: #ef5350;">Not configured</span>
            {% endif %}
        </dd>
```

**Step 2: Update device list template**

In `backend/devices/templates/devices/device_list.html`, replace the endpoint column (line 28):
```html
            <td>
                {{ device.effective_api_endpoint }}
                {% if not device.api_endpoint and device.effective_api_endpoint %}
                    <span class="badge badge-info">default</span>
                {% endif %}
                {% if not device.effective_api_endpoint %}
                    <span style="color: #ef5350;">No endpoint</span>
                {% endif %}
            </td>
```

**Step 3: Update device form template**

In `backend/devices/templates/devices/device_form.html`, add help text after the api_endpoint field (after line 35):
```html
        <div class="form-group">
            <label for="{{ form.api_endpoint.id_for_label }}">API Endpoint</label>
            {{ form.api_endpoint }}
            {% if form.api_endpoint.errors %}
            <div class="form-errors">{{ form.api_endpoint.errors }}</div>
            {% endif %}
            <span class="helptext">Leave blank to use the default endpoint.</span>
        </div>
```

**Step 4: Commit**

```bash
git add backend/devices/templates/
git commit -m "feat: show effective endpoint with default badge in device templates"
```

---

### Task 8: Add Settings API Endpoint (DRF)

**Files:**
- Create: `backend/settings/serializers.py`
- Create: `backend/settings/views.py`
- Create: `backend/settings/urls.py`
- Modify: `backend/config/urls.py`

**Step 1: Create serializer**

Create `backend/settings/serializers.py`:
```python
from rest_framework import serializers

from .models import SiteSettings


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = ["default_api_endpoint"]
```

**Step 2: Create view**

Create `backend/settings/views.py`:
```python
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import SiteSettings
from .serializers import SiteSettingsSerializer


@api_view(["GET", "PUT", "PATCH"])
def site_settings_view(request):
    settings = SiteSettings.load()
    if request.method == "GET":
        serializer = SiteSettingsSerializer(settings)
        return Response(serializer.data)
    serializer = SiteSettingsSerializer(settings, data=request.data, partial=request.method == "PATCH")
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

**Step 3: Create URL config**

Create `backend/settings/urls.py`:
```python
from django.urls import path

from . import views

urlpatterns = [
    path("settings/", views.site_settings_view, name="site-settings"),
]
```

**Step 4: Register in config/urls.py**

Add to the DRF API section:
```python
    path("api/v1/", include("settings.urls")),
```

**Step 5: Write API tests**

Add to `backend/settings/tests.py`:
```python
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class SiteSettingsAPITests(APITestCase):

    def test_get_settings(self):
        url = reverse("site-settings")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["default_api_endpoint"], "")

    def test_put_settings(self):
        url = reverse("site-settings")
        response = self.client.put(
            url, {"default_api_endpoint": "https://new.example.com/api"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["default_api_endpoint"], "https://new.example.com/api")

    def test_patch_settings(self):
        url = reverse("site-settings")
        response = self.client.patch(
            url, {"default_api_endpoint": "https://patched.example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["default_api_endpoint"], "https://patched.example.com")

    def test_put_invalid_url(self):
        url = reverse("site-settings")
        response = self.client.put(
            url, {"default_api_endpoint": "not-a-url"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_blank_clears_default(self):
        from .models import SiteSettings
        site = SiteSettings.load()
        site.default_api_endpoint = "https://old.example.com"
        site.save()

        url = reverse("site-settings")
        response = self.client.put(
            url, {"default_api_endpoint": ""}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["default_api_endpoint"], "")
```

**Step 6: Run tests**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py test settings --verbosity=2`
Expected: All tests PASS.

**Step 7: Commit**

```bash
git add backend/settings/serializers.py backend/settings/views.py backend/settings/urls.py backend/config/urls.py backend/settings/tests.py
git commit -m "feat: add DRF API endpoint for site settings"
```

---

### Task 9: Run Full Test Suite and Verify

**Step 1: Run all tests**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py test --verbosity=2`
Expected: All tests PASS with no regressions.

**Step 2: Fix any failures**

If any tests fail due to the api_endpoint becoming optional, update them accordingly. The existing tests all provide `api_endpoint` explicitly so they should still pass.

**Step 3: Final commit if any fixes were needed**

```bash
git add -A
git commit -m "fix: resolve test regressions from default endpoint changes"
```
