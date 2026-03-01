# Config Gather Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the hard-coded `api_endpoint`/`DeviceHeader` approach with a reusable, pluggable `ConfigGather` model that supports extensible transport types via a handler registry.

**Architecture:** A single `ConfigGather` model with `gather_type` (choice field) and `config` (JSONField) stores transport-specific settings. Devices, groups, and site settings each get an optional FK to ConfigGather, with resolution order: Device > Group > Site default. A handler registry maps gather types to fetch functions.

**Tech Stack:** Django 5.1, DRF, HTMX, pytest, JSONField

---

### Task 1: ConfigGather Model & Handler Registry

**Files:**
- Modify: `backend/devices/models.py`
- Create: `backend/devices/gather_handlers.py`
- Test: `backend/devices/tests.py`

**Step 1: Write the failing tests for ConfigGather model**

Add to `backend/devices/tests.py`:

```python
from .models import ConfigGather


class ConfigGatherModelTests(TestCase):
    """Tests for the ConfigGather model."""

    def test_create_config_gather(self):
        cg = ConfigGather.objects.create(
            name="HTTP REST",
            gather_type="http",
            config={"url": "https://example.com/api/{device_name}", "method": "GET"},
        )
        self.assertEqual(cg.name, "HTTP REST")
        self.assertEqual(cg.gather_type, "http")
        self.assertEqual(cg.config["url"], "https://example.com/api/{device_name}")
        self.assertIsNotNone(cg.created_at)
        self.assertIsNotNone(cg.updated_at)

    def test_config_gather_str(self):
        cg = ConfigGather.objects.create(
            name="My Gatherer",
            gather_type="http",
            config={},
        )
        self.assertEqual(str(cg), "My Gatherer")

    def test_config_gather_unique_name(self):
        ConfigGather.objects.create(name="unique", gather_type="http", config={})
        with self.assertRaises(IntegrityError):
            ConfigGather.objects.create(name="unique", gather_type="http", config={})

    def test_config_gather_ordering(self):
        ConfigGather.objects.create(name="Zebra", gather_type="http", config={})
        ConfigGather.objects.create(name="Alpha", gather_type="http", config={})
        names = list(ConfigGather.objects.values_list("name", flat=True))
        self.assertEqual(names, ["Alpha", "Zebra"])

    def test_config_gather_default_config(self):
        cg = ConfigGather.objects.create(name="Empty", gather_type="http")
        self.assertEqual(cg.config, {})

    def test_config_gather_default_gather_type(self):
        cg = ConfigGather.objects.create(name="Default Type", config={})
        self.assertEqual(cg.gather_type, "http")
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest devices/tests.py::ConfigGatherModelTests -v`
Expected: ImportError — ConfigGather does not exist yet.

**Step 3: Write the ConfigGather model**

Add to `backend/devices/models.py` (before DeviceGroup):

```python
class ConfigGather(models.Model):
    GATHER_TYPES = [
        ("http", "HTTP/REST"),
    ]

    name = models.CharField(max_length=255, unique=True)
    gather_type = models.CharField(
        max_length=50, choices=GATHER_TYPES, default="http"
    )
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
```

**Step 4: Create and run the migration**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py makemigrations devices -n add_config_gather && python manage.py migrate`

**Step 5: Run tests to verify they pass**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest devices/tests.py::ConfigGatherModelTests -v`
Expected: All PASS.

**Step 6: Write the handler registry**

Create `backend/devices/gather_handlers.py`:

```python
"""
Pluggable config-gather handler registry.

Each handler is a function that takes a ConfigGather instance and a Device
and returns the fetched configuration text. Register new transport types
with the @register_handler decorator.
"""

import requests

GATHER_HANDLERS = {}


def register_handler(gather_type):
    """Register a config-gather handler for the given type."""
    def decorator(fn):
        GATHER_HANDLERS[gather_type] = fn
        return fn
    return decorator


@register_handler("http")
def http_handler(config_gather, device):
    """Fetch device configuration via HTTP/REST."""
    cfg = config_gather.config
    url = cfg.get("url", "")
    if not url:
        raise ValueError("ConfigGather HTTP config missing 'url'.")
    url = url.replace("{device_name}", device.name)
    method = cfg.get("method", "GET")
    headers = cfg.get("headers", {})
    timeout = cfg.get("timeout", 30)
    verify = cfg.get("verify_ssl", True)

    response = requests.request(
        method, url, headers=headers, timeout=timeout, verify=verify
    )
    response.raise_for_status()
    return response.text


def validate_config(gather_type, config):
    """
    Validate the config dict for a given gather_type.
    Returns a list of error strings (empty if valid).
    """
    errors = []
    if gather_type == "http":
        if not config.get("url"):
            errors.append("HTTP config requires a 'url' field.")
    return errors
```

**Step 7: Write tests for the handler registry**

Add to `backend/devices/tests.py`:

```python
from unittest.mock import Mock, patch

from .gather_handlers import GATHER_HANDLERS, http_handler, validate_config


class GatherHandlerRegistryTests(TestCase):
    """Tests for the gather handler registry."""

    def test_http_handler_registered(self):
        self.assertIn("http", GATHER_HANDLERS)

    def test_validate_config_http_requires_url(self):
        errors = validate_config("http", {})
        self.assertEqual(len(errors), 1)
        self.assertIn("url", errors[0])

    def test_validate_config_http_valid(self):
        errors = validate_config("http", {"url": "https://example.com/{device_name}"})
        self.assertEqual(errors, [])


class HttpHandlerTests(TestCase):
    """Tests for the HTTP gather handler."""

    def setUp(self):
        self.cg = ConfigGather.objects.create(
            name="Test HTTP",
            gather_type="http",
            config={
                "url": "https://api.example.com/{device_name}",
                "method": "GET",
                "headers": {"Authorization": "Bearer token123"},
                "timeout": 15,
                "verify_ssl": True,
            },
        )
        self.device = Device.objects.create(
            name="switch-01",
            hostname="switch-01.local",
        )

    @patch("devices.gather_handlers.requests.request")
    def test_http_handler_success(self, mock_request):
        mock_response = Mock()
        mock_response.text = "hostname switch-01"
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        result = http_handler(self.cg, self.device)

        self.assertEqual(result, "hostname switch-01")
        mock_request.assert_called_once_with(
            "GET",
            "https://api.example.com/switch-01",
            headers={"Authorization": "Bearer token123"},
            timeout=15,
            verify=True,
        )

    @patch("devices.gather_handlers.requests.request")
    def test_http_handler_replaces_device_name(self, mock_request):
        mock_response = Mock()
        mock_response.text = "config"
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        http_handler(self.cg, self.device)

        called_url = mock_request.call_args[0][1]
        self.assertEqual(called_url, "https://api.example.com/switch-01")

    def test_http_handler_missing_url_raises(self):
        self.cg.config = {}
        self.cg.save()
        with self.assertRaises(ValueError):
            http_handler(self.cg, self.device)

    @patch("devices.gather_handlers.requests.request")
    def test_http_handler_defaults(self, mock_request):
        """When method/headers/timeout/verify_ssl are omitted, defaults are used."""
        self.cg.config = {"url": "https://example.com/{device_name}"}
        self.cg.save()
        mock_response = Mock()
        mock_response.text = "config"
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response

        http_handler(self.cg, self.device)

        mock_request.assert_called_once_with(
            "GET",
            "https://example.com/switch-01",
            headers={},
            timeout=30,
            verify=True,
        )
```

**Step 8: Run all handler tests**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest devices/tests.py::GatherHandlerRegistryTests devices/tests.py::HttpHandlerTests -v`
Expected: All PASS.

**Step 9: Commit**

```bash
git add backend/devices/models.py backend/devices/gather_handlers.py backend/devices/tests.py backend/devices/migrations/
git commit -m "feat: add ConfigGather model and handler registry"
```

---

### Task 2: Add ConfigGather FKs to Device, DeviceGroup, SiteSettings

**Files:**
- Modify: `backend/devices/models.py`
- Modify: `backend/settings/models.py`
- Test: `backend/devices/tests.py`
- Test: `backend/settings/tests.py`

**Step 1: Write failing tests for FK relationships and effective_config_gather**

Add to `backend/devices/tests.py`:

```python
class DeviceConfigGatherTests(TestCase):
    """Tests for ConfigGather FK on Device and resolution."""

    def setUp(self):
        self.cg = ConfigGather.objects.create(
            name="Device Gatherer",
            gather_type="http",
            config={"url": "https://device.example.com/{device_name}"},
        )

    def test_device_config_gather_fk(self):
        device = Device.objects.create(
            name="d1", hostname="d1.local", config_gather=self.cg,
        )
        self.assertEqual(device.config_gather, self.cg)

    def test_device_config_gather_nullable(self):
        device = Device.objects.create(name="d2", hostname="d2.local")
        self.assertIsNone(device.config_gather)

    def test_effective_config_gather_from_device(self):
        device = Device.objects.create(
            name="d3", hostname="d3.local", config_gather=self.cg,
        )
        self.assertEqual(device.effective_config_gather, self.cg)

    def test_effective_config_gather_from_group(self):
        group_cg = ConfigGather.objects.create(
            name="Group Gatherer", gather_type="http",
            config={"url": "https://group.example.com/{device_name}"},
        )
        group = DeviceGroup.objects.create(name="G1", config_gather=group_cg)
        device = Device.objects.create(name="d4", hostname="d4.local")
        device.groups.add(group)
        self.assertEqual(device.effective_config_gather, group_cg)

    def test_effective_config_gather_device_overrides_group(self):
        group_cg = ConfigGather.objects.create(
            name="Group Gatherer 2", gather_type="http",
            config={"url": "https://group.example.com/{device_name}"},
        )
        group = DeviceGroup.objects.create(name="G2", config_gather=group_cg)
        device = Device.objects.create(
            name="d5", hostname="d5.local", config_gather=self.cg,
        )
        device.groups.add(group)
        self.assertEqual(device.effective_config_gather, self.cg)

    def test_effective_config_gather_from_site_default(self):
        from settings.models import SiteSettings
        site_cg = ConfigGather.objects.create(
            name="Site Default", gather_type="http",
            config={"url": "https://site.example.com/{device_name}"},
        )
        site = SiteSettings.load()
        site.default_config_gather = site_cg
        site.save()
        device = Device.objects.create(name="d6", hostname="d6.local")
        self.assertEqual(device.effective_config_gather, site_cg)

    def test_effective_config_gather_none_when_unconfigured(self):
        device = Device.objects.create(name="d7", hostname="d7.local")
        self.assertIsNone(device.effective_config_gather)

    def test_config_gather_set_null_on_delete(self):
        device = Device.objects.create(
            name="d8", hostname="d8.local", config_gather=self.cg,
        )
        self.cg.delete()
        device.refresh_from_db()
        self.assertIsNone(device.config_gather)


class DeviceGroupConfigGatherTests(TestCase):
    """Tests for ConfigGather FK on DeviceGroup."""

    def test_group_config_gather_fk(self):
        cg = ConfigGather.objects.create(
            name="Group CG", gather_type="http", config={},
        )
        group = DeviceGroup.objects.create(name="G1", config_gather=cg)
        self.assertEqual(group.config_gather, cg)

    def test_group_config_gather_nullable(self):
        group = DeviceGroup.objects.create(name="G2")
        self.assertIsNone(group.config_gather)

    def test_group_config_gather_set_null_on_delete(self):
        cg = ConfigGather.objects.create(
            name="Group CG 2", gather_type="http", config={},
        )
        group = DeviceGroup.objects.create(name="G3", config_gather=cg)
        cg.delete()
        group.refresh_from_db()
        self.assertIsNone(group.config_gather)
```

Add to `backend/settings/tests.py`:

```python
from devices.models import ConfigGather


class SiteSettingsConfigGatherTests(TestCase):

    def test_default_config_gather_fk(self):
        cg = ConfigGather.objects.create(
            name="Site CG", gather_type="http",
            config={"url": "https://site.example.com/{device_name}"},
        )
        site = SiteSettings.load()
        site.default_config_gather = cg
        site.save()
        site.refresh_from_db()
        self.assertEqual(site.default_config_gather, cg)

    def test_default_config_gather_nullable(self):
        site = SiteSettings.load()
        self.assertIsNone(site.default_config_gather)

    def test_default_config_gather_set_null_on_delete(self):
        cg = ConfigGather.objects.create(
            name="Site CG 2", gather_type="http", config={},
        )
        site = SiteSettings.load()
        site.default_config_gather = cg
        site.save()
        cg.delete()
        site.refresh_from_db()
        self.assertIsNone(site.default_config_gather)
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest devices/tests.py::DeviceConfigGatherTests devices/tests.py::DeviceGroupConfigGatherTests settings/tests.py::SiteSettingsConfigGatherTests -v`
Expected: FAIL — fields don't exist yet.

**Step 3: Add the FK fields and effective_config_gather property**

In `backend/devices/models.py`:

Add to DeviceGroup model:
```python
    config_gather = models.ForeignKey(
        "ConfigGather",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="device_groups",
    )
```

Add to Device model (replace `api_endpoint` field and `effective_api_endpoint` property):
```python
    config_gather = models.ForeignKey(
        "ConfigGather",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="devices_direct",
    )

    @property
    def effective_config_gather(self):
        if self.config_gather:
            return self.config_gather
        for group in self.groups.all():
            if group.config_gather:
                return group.config_gather
        from settings.models import SiteSettings
        site = SiteSettings.load()
        return site.default_config_gather
```

In `backend/settings/models.py`:

Add to SiteSettings:
```python
    default_config_gather = models.ForeignKey(
        "devices.ConfigGather",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
```

**Note:** Keep the old `api_endpoint`, `DeviceHeader`, `default_api_endpoint`, and `effective_api_endpoint` fields for now — they'll be removed in Task 6 (data migration). The new FK fields are added alongside them.

**Step 4: Create and run migration**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py makemigrations devices settings -n add_config_gather_fks && python manage.py migrate`

**Step 5: Run tests to verify they pass**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest devices/tests.py::DeviceConfigGatherTests devices/tests.py::DeviceGroupConfigGatherTests settings/tests.py::SiteSettingsConfigGatherTests -v`
Expected: All PASS.

**Step 6: Commit**

```bash
git add backend/devices/models.py backend/settings/models.py backend/devices/tests.py backend/settings/tests.py backend/devices/migrations/ backend/settings/migrations/
git commit -m "feat: add ConfigGather FK to Device, DeviceGroup, SiteSettings"
```

---

### Task 3: Update Audit Service to Use ConfigGather

**Files:**
- Modify: `backend/audits/services.py`
- Modify: `backend/devices/views.py` (test_connection API action)
- Modify: `backend/devices/views_html.py` (test_connection HTML view)
- Test: `backend/audits/tests.py`
- Test: `backend/devices/tests.py`

**Step 1: Write failing test for _fetch_config using ConfigGather**

Add to `backend/audits/tests.py`:

```python
from devices.models import ConfigGather


class FetchConfigTests(AuditFixtureMixin, TestCase):
    """Tests for _fetch_config using ConfigGather."""

    def test_fetch_config_uses_config_gather(self):
        cg = ConfigGather.objects.create(
            name="Test CG",
            gather_type="http",
            config={
                "url": "https://api.example.com/{device_name}",
                "method": "GET",
                "headers": {"Authorization": "Bearer token"},
                "timeout": 15,
            },
        )
        device = self.create_device(config_gather=cg)
        from audits.services import _fetch_config

        with patch("devices.gather_handlers.requests.request") as mock_request:
            mock_response = Mock()
            mock_response.text = "hostname switch-01"
            mock_response.raise_for_status = Mock()
            mock_request.return_value = mock_response

            result = _fetch_config(device)

        self.assertEqual(result, "hostname switch-01")
        mock_request.assert_called_once_with(
            "GET",
            "https://api.example.com/switch-01",
            headers={"Authorization": "Bearer token"},
            timeout=15,
            verify=True,
        )

    def test_fetch_config_no_config_gather_raises(self):
        device = self.create_device()
        device.config_gather = None
        device.save()
        from audits.services import _fetch_config

        with self.assertRaises(ValueError):
            _fetch_config(device)

    def test_fetch_config_unknown_gather_type_raises(self):
        cg = ConfigGather.objects.create(
            name="Unknown CG",
            gather_type="unknown",
            config={},
        )
        device = self.create_device(config_gather=cg)
        from audits.services import _fetch_config

        with self.assertRaises(ValueError):
            _fetch_config(device)
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest audits/tests.py::FetchConfigTests -v`
Expected: FAIL

**Step 3: Update _fetch_config in audits/services.py**

Replace the `_fetch_config` function:

```python
def _fetch_config(device):
    """
    Retrieve the device configuration using its effective ConfigGather.

    Uses device.effective_config_gather which resolves via:
    Device > Group > Site default.
    """
    from devices.gather_handlers import GATHER_HANDLERS

    cg = device.effective_config_gather
    if not cg:
        raise ValueError(
            f"Device '{device.name}' has no config gather configured "
            "and no default is set."
        )
    handler = GATHER_HANDLERS.get(cg.gather_type)
    if not handler:
        raise ValueError(f"Unknown gather type: {cg.gather_type}")
    return handler(cg, device)
```

Remove the `import requests` at the top of the file (no longer needed directly).
Remove the old `headers = {h.key: h.value ...}` logic.

**Step 4: Run tests to verify they pass**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest audits/tests.py::FetchConfigTests -v`
Expected: All PASS.

**Step 5: Update test_connection in DRF views**

In `backend/devices/views.py`, update the `test_connection` action:

```python
    @action(detail=True, methods=["post"])
    def test_connection(self, request, pk=None):
        device = self.get_object()
        cg = device.effective_config_gather
        if not cg:
            return Response(
                {"success": False, "error": "No config gather configured and no default is set."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from .gather_handlers import GATHER_HANDLERS
        handler = GATHER_HANDLERS.get(cg.gather_type)
        if not handler:
            return Response(
                {"success": False, "error": f"Unknown gather type: {cg.gather_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            config_text = handler(cg, device)
            return Response(
                {
                    "success": True,
                    "content_length": len(config_text),
                }
            )
        except Exception as exc:
            return Response(
                {"success": False, "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
```

Remove the `import requests` at the top of `views.py`.

**Step 6: Update test_connection in HTML views**

In `backend/devices/views_html.py`, update `device_test_connection`:

```python
@require_POST
def device_test_connection(request, pk):
    device = get_object_or_404(Device, pk=pk)
    cg = device.effective_config_gather
    if not cg:
        html = render_to_string(
            "devices/partials/test_result.html",
            {
                "success": False,
                "error": "No config gather configured and no default is set.",
            },
        )
        return HttpResponse(html)
    from .gather_handlers import GATHER_HANDLERS
    handler = GATHER_HANDLERS.get(cg.gather_type)
    if not handler:
        html = render_to_string(
            "devices/partials/test_result.html",
            {
                "success": False,
                "error": f"Unknown gather type: {cg.gather_type}",
            },
        )
        return HttpResponse(html)
    try:
        config_text = handler(cg, device)
        html = render_to_string(
            "devices/partials/test_result.html",
            {
                "success": True,
                "content_length": len(config_text),
            },
        )
    except Exception as exc:
        html = render_to_string(
            "devices/partials/test_result.html",
            {
                "success": False,
                "error": str(exc),
            },
        )
    return HttpResponse(html)
```

Remove `import requests as http_requests` from the top of `views_html.py`.

**Step 7: Update existing test_connection tests**

Update the test_connection tests in `backend/devices/tests.py` to use ConfigGather instead of api_endpoint/DeviceHeader. The mock target changes from `devices.views.requests.get` to `devices.gather_handlers.requests.request`.

**Step 8: Run all tests**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest devices/tests.py audits/tests.py -v`
Expected: All PASS (some existing tests that reference `api_endpoint` may still work since the field still exists).

**Step 9: Commit**

```bash
git add backend/audits/services.py backend/devices/views.py backend/devices/views_html.py backend/devices/tests.py backend/audits/tests.py
git commit -m "feat: update audit service and test_connection to use ConfigGather"
```

---

### Task 4: ConfigGather CRUD — DRF API

**Files:**
- Modify: `backend/devices/serializers.py`
- Modify: `backend/devices/views.py`
- Modify: `backend/devices/urls.py`
- Test: `backend/devices/tests.py`

**Step 1: Write failing tests for ConfigGather API**

Add to `backend/devices/tests.py`:

```python
class ConfigGatherAPITests(APITestCase):
    """Tests for the ConfigGather REST API endpoints."""

    def setUp(self):
        self.cg = ConfigGather.objects.create(
            name="HTTP Gatherer",
            gather_type="http",
            config={"url": "https://example.com/{device_name}", "method": "GET"},
        )
        self.list_url = reverse("configgather-list")
        self.detail_url = reverse("configgather-detail", kwargs={"pk": self.cg.pk})

    def test_list_config_gathers(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "HTTP Gatherer")

    def test_create_config_gather(self):
        data = {
            "name": "New Gatherer",
            "gather_type": "http",
            "config": {"url": "https://new.example.com/{device_name}"},
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ConfigGather.objects.count(), 2)

    def test_create_config_gather_validates_config(self):
        data = {
            "name": "Bad Config",
            "gather_type": "http",
            "config": {},
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_config_gather(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "HTTP Gatherer")
        self.assertEqual(response.data["gather_type"], "http")
        self.assertIn("config", response.data)

    def test_update_config_gather(self):
        data = {
            "name": "Updated",
            "gather_type": "http",
            "config": {"url": "https://updated.com/{device_name}"},
        }
        response = self.client.put(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cg.refresh_from_db()
        self.assertEqual(self.cg.name, "Updated")

    def test_delete_config_gather(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ConfigGather.objects.filter(pk=self.cg.pk).exists())

    def test_list_includes_usage_count(self):
        device = Device.objects.create(
            name="d1", hostname="d1.local", config_gather=self.cg,
        )
        response = self.client.get(self.list_url)
        self.assertIn("usage_count", response.data["results"][0])
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest devices/tests.py::ConfigGatherAPITests -v`
Expected: FAIL — no URL registered yet.

**Step 3: Create serializer**

Add to `backend/devices/serializers.py`:

```python
from .gather_handlers import validate_config
from .models import ConfigGather


class ConfigGatherSerializer(serializers.ModelSerializer):
    usage_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ConfigGather
        fields = [
            "id",
            "name",
            "gather_type",
            "config",
            "usage_count",
            "created_at",
            "updated_at",
        ]

    def get_usage_count(self, obj):
        return (
            obj.devices_direct.count()
            + obj.device_groups.count()
        )

    def validate(self, data):
        gather_type = data.get("gather_type", self.instance.gather_type if self.instance else "http")
        config = data.get("config", self.instance.config if self.instance else {})
        errors = validate_config(gather_type, config)
        if errors:
            raise serializers.ValidationError({"config": errors})
        return data
```

**Step 4: Create viewset**

Add to `backend/devices/views.py`:

```python
from .models import ConfigGather
from .serializers import ConfigGatherSerializer


class ConfigGatherViewSet(viewsets.ModelViewSet):
    queryset = ConfigGather.objects.all()
    serializer_class = ConfigGatherSerializer
    search_fields = ["name"]
```

**Step 5: Register URL**

In `backend/devices/urls.py`, add:

```python
from .views import ConfigGatherViewSet

router.register("config-gatherers", ConfigGatherViewSet)
```

**Step 6: Run tests to verify they pass**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest devices/tests.py::ConfigGatherAPITests -v`
Expected: All PASS.

**Step 7: Commit**

```bash
git add backend/devices/serializers.py backend/devices/views.py backend/devices/urls.py backend/devices/tests.py
git commit -m "feat: add ConfigGather DRF API with validation"
```

---

### Task 5: ConfigGather CRUD — HTML UI

**Files:**
- Create: `backend/devices/templates/devices/configgather_list.html`
- Create: `backend/devices/templates/devices/configgather_form.html`
- Create: `backend/devices/templates/devices/configgather_detail.html`
- Create: `backend/devices/urls_html_configgatherers.py`
- Modify: `backend/devices/forms.py`
- Modify: `backend/devices/views_html.py`
- Modify: `backend/config/urls.py`
- Modify: `backend/templates/partials/sidebar.html`

**Step 1: Create the ConfigGather form**

Add to `backend/devices/forms.py`:

```python
from .gather_handlers import validate_config
from .models import ConfigGather


class ConfigGatherForm(forms.ModelForm):
    url = forms.URLField(required=True)
    method = forms.ChoiceField(
        choices=[("GET", "GET"), ("POST", "POST")],
        initial="GET",
        required=False,
    )
    timeout = forms.IntegerField(initial=30, required=False)
    verify_ssl = forms.BooleanField(initial=True, required=False)
    http_headers = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Key: Value (one per line)"}),
        required=False,
        help_text="One header per line in Key: Value format.",
    )

    class Meta:
        model = ConfigGather
        fields = ["name", "gather_type"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.config:
            cfg = self.instance.config
            self.fields["url"].initial = cfg.get("url", "")
            self.fields["method"].initial = cfg.get("method", "GET")
            self.fields["timeout"].initial = cfg.get("timeout", 30)
            self.fields["verify_ssl"].initial = cfg.get("verify_ssl", True)
            headers = cfg.get("headers", {})
            self.fields["http_headers"].initial = "\n".join(
                f"{k}: {v}" for k, v in headers.items()
            )

    def clean(self):
        cleaned = super().clean()
        headers = {}
        raw_headers = cleaned.get("http_headers", "")
        for line in raw_headers.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" not in line:
                raise forms.ValidationError(f"Invalid header format: {line}")
            key, _, value = line.partition(":")
            headers[key.strip()] = value.strip()

        config = {
            "url": cleaned.get("url", ""),
            "method": cleaned.get("method", "GET"),
            "headers": headers,
            "timeout": cleaned.get("timeout", 30),
            "verify_ssl": cleaned.get("verify_ssl", True),
        }
        errors = validate_config(cleaned.get("gather_type", "http"), config)
        if errors:
            raise forms.ValidationError(errors)
        cleaned["_config"] = config
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.config = self.cleaned_data["_config"]
        if commit:
            instance.save()
        return instance
```

**Step 2: Create the views**

Add to `backend/devices/views_html.py`:

```python
from .forms import ConfigGatherForm
from .models import ConfigGather


class ConfigGatherListView(generic.ListView):
    model = ConfigGather
    template_name = "devices/configgather_list.html"
    context_object_name = "config_gatherers"


class ConfigGatherCreateView(generic.CreateView):
    model = ConfigGather
    form_class = ConfigGatherForm
    template_name = "devices/configgather_form.html"

    def form_valid(self, form):
        cg = form.save()
        messages.success(self.request, f'Config gatherer "{cg.name}" created.')
        return redirect("configgather-list-html")


class ConfigGatherUpdateView(generic.UpdateView):
    model = ConfigGather
    form_class = ConfigGatherForm
    template_name = "devices/configgather_form.html"

    def form_valid(self, form):
        cg = form.save()
        messages.success(self.request, f'Config gatherer "{cg.name}" updated.')
        return redirect("configgather-list-html")


class ConfigGatherDetailView(generic.DetailView):
    model = ConfigGather
    template_name = "devices/configgather_detail.html"
    context_object_name = "config_gather"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        cg = self.object
        ctx["devices_using"] = Device.objects.filter(config_gather=cg)
        ctx["groups_using"] = DeviceGroup.objects.filter(config_gather=cg)
        return ctx


@require_POST
def configgather_delete(request, pk):
    cg = get_object_or_404(ConfigGather, pk=pk)
    name = cg.name
    cg.delete()
    messages.success(request, f'Config gatherer "{name}" deleted.')
    return redirect("configgather-list-html")
```

**Step 3: Create URL patterns**

Create `backend/devices/urls_html_configgatherers.py`:

```python
from django.urls import path

from . import views_html

urlpatterns = [
    path("", views_html.ConfigGatherListView.as_view(), name="configgather-list-html"),
    path("new/", views_html.ConfigGatherCreateView.as_view(), name="configgather-create-html"),
    path("<int:pk>/", views_html.ConfigGatherDetailView.as_view(), name="configgather-detail-html"),
    path("<int:pk>/edit/", views_html.ConfigGatherUpdateView.as_view(), name="configgather-update-html"),
    path("<int:pk>/delete/", views_html.configgather_delete, name="configgather-delete-html"),
]
```

**Step 4: Register in main urls.py**

Add to `backend/config/urls.py`:

```python
    path("config-gatherers/", include("devices.urls_html_configgatherers")),
```

**Step 5: Create templates**

Create `backend/devices/templates/devices/configgather_list.html`:

```html
{% extends "base.html" %}

{% block title %}Config Gatherers — Netaudit{% endblock %}

{% block content %}
<div class="page-header">
    <h2>Config Gatherers</h2>
    <a href="{% url 'configgather-create-html' %}" class="btn btn-primary">Add Config Gatherer</a>
</div>

{% if config_gatherers %}
<table class="data-table">
    <thead>
        <tr>
            <th>Name</th>
            <th>Type</th>
            <th>URL</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        {% for cg in config_gatherers %}
        <tr>
            <td><a href="{% url 'configgather-detail-html' cg.pk %}">{{ cg.name }}</a></td>
            <td>{{ cg.get_gather_type_display }}</td>
            <td>{{ cg.config.url|default:"—" }}</td>
            <td>
                <div class="btn-group">
                    <a href="{% url 'configgather-update-html' cg.pk %}" class="btn btn-secondary btn-sm">Edit</a>
                    <button class="btn btn-danger btn-sm"
                            hx-post="{% url 'configgather-delete-html' cg.pk %}"
                            hx-confirm="Are you sure you want to delete &quot;{{ cg.name }}&quot;?">
                        Delete
                    </button>
                </div>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% else %}
<div class="empty-state">
    <p>No config gatherers configured yet.</p>
    <a href="{% url 'configgather-create-html' %}" class="btn btn-primary">Add your first config gatherer</a>
</div>
{% endif %}
{% endblock %}
```

Create `backend/devices/templates/devices/configgather_form.html`:

```html
{% extends "base.html" %}

{% block title %}{% if object %}Edit Config Gatherer — {{ object.name }}{% else %}Add Config Gatherer{% endif %} — Netaudit{% endblock %}

{% block content %}
<div class="page-header">
    <h2>{% if object %}Edit Config Gatherer{% else %}Add Config Gatherer{% endif %}</h2>
</div>

<form method="post">
    {% csrf_token %}

    <div class="card">
        <h3>General</h3>

        <div class="form-group">
            <label for="{{ form.name.id_for_label }}">Name</label>
            {{ form.name }}
            {% if form.name.errors %}<div class="form-errors">{{ form.name.errors }}</div>{% endif %}
        </div>

        <div class="form-group">
            <label for="{{ form.gather_type.id_for_label }}">Type</label>
            {{ form.gather_type }}
            {% if form.gather_type.errors %}<div class="form-errors">{{ form.gather_type.errors }}</div>{% endif %}
        </div>
    </div>

    <div class="card">
        <h3>HTTP Settings</h3>

        <div class="form-group">
            <label for="{{ form.url.id_for_label }}">URL</label>
            {{ form.url }}
            {% if form.url.errors %}<div class="form-errors">{{ form.url.errors }}</div>{% endif %}
            <span class="helptext">Use {device_name} as a placeholder. Example: https://api.example.com/config/{device_name}</span>
        </div>

        <div class="form-group">
            <label for="{{ form.method.id_for_label }}">Method</label>
            {{ form.method }}
            {% if form.method.errors %}<div class="form-errors">{{ form.method.errors }}</div>{% endif %}
        </div>

        <div class="form-group">
            <label for="{{ form.http_headers.id_for_label }}">Headers</label>
            {{ form.http_headers }}
            {% if form.http_headers.errors %}<div class="form-errors">{{ form.http_headers.errors }}</div>{% endif %}
            <span class="helptext">One per line. Example: Authorization: Bearer mytoken</span>
        </div>

        <div class="form-group">
            <label for="{{ form.timeout.id_for_label }}">Timeout (seconds)</label>
            {{ form.timeout }}
            {% if form.timeout.errors %}<div class="form-errors">{{ form.timeout.errors }}</div>{% endif %}
        </div>

        <div class="form-group">
            <label class="checkbox-label">
                {{ form.verify_ssl }} Verify SSL
            </label>
            {% if form.verify_ssl.errors %}<div class="form-errors">{{ form.verify_ssl.errors }}</div>{% endif %}
        </div>
    </div>

    <div class="actions">
        <button type="submit" class="btn btn-primary">
            {% if object %}Update Config Gatherer{% else %}Create Config Gatherer{% endif %}
        </button>
        <a href="{% url 'configgather-list-html' %}" class="btn btn-secondary">Cancel</a>
    </div>
</form>
{% endblock %}
```

Create `backend/devices/templates/devices/configgather_detail.html`:

```html
{% extends "base.html" %}

{% block title %}{{ config_gather.name }} — Netaudit{% endblock %}

{% block content %}
<div class="page-header">
    <h2>{{ config_gather.name }}</h2>
    <div class="btn-group">
        <a href="{% url 'configgather-update-html' config_gather.pk %}" class="btn btn-secondary">Edit</a>
        <button class="btn btn-danger"
                hx-post="{% url 'configgather-delete-html' config_gather.pk %}"
                hx-confirm="Are you sure you want to delete &quot;{{ config_gather.name }}&quot;?">
            Delete
        </button>
    </div>
</div>

<div class="card">
    <h3>Configuration</h3>
    <dl class="detail-grid">
        <dt>Type</dt>
        <dd>{{ config_gather.get_gather_type_display }}</dd>

        <dt>URL</dt>
        <dd>{{ config_gather.config.url|default:"—" }}</dd>

        <dt>Method</dt>
        <dd>{{ config_gather.config.method|default:"GET" }}</dd>

        <dt>Timeout</dt>
        <dd>{{ config_gather.config.timeout|default:"30" }}s</dd>

        <dt>Verify SSL</dt>
        <dd>{% if config_gather.config.verify_ssl|default:True %}Yes{% else %}No{% endif %}</dd>

        <dt>Created</dt>
        <dd>{{ config_gather.created_at }}</dd>

        <dt>Updated</dt>
        <dd>{{ config_gather.updated_at }}</dd>
    </dl>
</div>

{% if config_gather.config.headers %}
<div class="card">
    <h3>Headers</h3>
    <table class="data-table">
        <thead>
            <tr>
                <th>Key</th>
                <th>Value</th>
            </tr>
        </thead>
        <tbody>
            {% for key, value in config_gather.config.headers.items %}
            <tr>
                <td>{{ key }}</td>
                <td>{{ value }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
{% endif %}

{% if devices_using %}
<div class="card">
    <h3>Devices Using This Gatherer</h3>
    <ul>
        {% for device in devices_using %}
        <li><a href="{% url 'device-detail-html' device.pk %}">{{ device.name }}</a></li>
        {% endfor %}
    </ul>
</div>
{% endif %}

{% if groups_using %}
<div class="card">
    <h3>Groups Using This Gatherer</h3>
    <ul>
        {% for group in groups_using %}
        <li><a href="{% url 'group-detail-html' group.pk %}">{{ group.name }}</a></li>
        {% endfor %}
    </ul>
</div>
{% endif %}
{% endblock %}
```

**Step 6: Add sidebar link**

In `backend/templates/partials/sidebar.html`, add after the Groups link:

```html
        <li><a href="{% url 'configgather-list-html' %}" class="{% active_class request '/config-gatherers/' %}">Config Gatherers</a></li>
```

**Step 7: Commit**

```bash
git add backend/devices/forms.py backend/devices/views_html.py backend/devices/urls_html_configgatherers.py backend/devices/templates/devices/configgather_*.html backend/config/urls.py backend/templates/partials/sidebar.html
git commit -m "feat: add ConfigGather HTML CRUD pages and sidebar"
```

---

### Task 6: Update Device/Group/Settings Forms to Use ConfigGather

**Files:**
- Modify: `backend/devices/forms.py`
- Modify: `backend/devices/views_html.py`
- Modify: `backend/devices/templates/devices/device_form.html`
- Modify: `backend/devices/templates/devices/device_detail.html`
- Modify: `backend/devices/templates/devices/device_list.html`
- Modify: `backend/devices/templates/devices/group_form.html`
- Modify: `backend/devices/templates/devices/group_detail.html`
- Modify: `backend/settings/forms.py`
- Modify: `backend/settings/templates/settings/settings_form.html`
- Modify: `backend/devices/serializers.py`

**Step 1: Update DeviceForm**

In `backend/devices/forms.py`, update DeviceForm:
- Remove `api_endpoint` from fields
- Add `config_gather` as optional ModelChoiceField
- Remove `DeviceHeaderFormSet`

```python
class DeviceForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=DeviceGroup.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    config_gather = forms.ModelChoiceField(
        queryset=ConfigGather.objects.all(),
        required=False,
        help_text="Leave blank to inherit from group or site default.",
    )

    class Meta:
        model = Device
        fields = ["name", "hostname", "config_gather", "enabled", "groups"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["groups"].initial = self.instance.groups.all()

    def save(self, commit=True):
        device = super().save(commit=commit)
        if commit:
            device.groups.set(self.cleaned_data["groups"])
        return device
```

**Step 2: Update DeviceGroupForm**

Add `config_gather` field:

```python
class DeviceGroupForm(forms.ModelForm):
    devices = forms.ModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    config_gather = forms.ModelChoiceField(
        queryset=ConfigGather.objects.all(),
        required=False,
        help_text="Config gatherer for all devices in this group.",
    )

    class Meta:
        model = DeviceGroup
        fields = ["name", "description", "config_gather", "devices"]
    ...
```

**Step 3: Update SiteSettingsForm**

In `backend/settings/forms.py`:

```python
from devices.models import ConfigGather


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = ["default_config_gather"]
```

**Step 4: Update views_html.py**

Remove `DeviceHeaderFormSet` from imports and all references in DeviceCreateView and DeviceUpdateView. Remove the `device_header_add` view. Remove `import requests as http_requests`.

**Step 5: Update device_form.html template**

Replace the `api_endpoint` field with `config_gather` dropdown. Remove the entire Headers card and the JS script. Keep the existing template structure.

**Step 6: Update device_detail.html template**

Replace the "API Endpoint" section with "Config Gather" showing the effective config gather name with inheritance badge. Replace the "Headers" section — remove it entirely. Show the config gather name as a link to its detail page.

**Step 7: Update device_list.html template**

Replace the "Endpoint" column with "Config Gather" showing the effective config gather name.

**Step 8: Update group_form.html template**

Add `config_gather` dropdown field.

**Step 9: Update group_detail.html template**

Show the config gather if assigned.

**Step 10: Update settings_form.html template**

Replace `default_api_endpoint` field with `default_config_gather` dropdown.

**Step 11: Update Device/Group serializers**

Update `DeviceSerializer` to include `config_gather` FK and `effective_config_gather` (read-only name). Remove `api_endpoint`, `effective_api_endpoint`, and `headers` fields.

Update `DeviceGroupSerializer` to include `config_gather` FK.

Remove `DeviceHeaderSerializer`.

**Step 12: Commit**

```bash
git add backend/devices/forms.py backend/devices/views_html.py backend/devices/serializers.py backend/devices/templates/ backend/settings/forms.py backend/settings/templates/ backend/devices/urls_html.py
git commit -m "feat: update Device/Group/Settings UI to use ConfigGather"
```

---

### Task 7: Data Migration & Cleanup

**Files:**
- Create: data migration in `backend/devices/migrations/`
- Create: schema migration in `backend/devices/migrations/` (remove old fields)
- Create: schema migration in `backend/settings/migrations/` (remove old field)
- Modify: `backend/devices/models.py` (remove old fields)
- Modify: `backend/settings/models.py` (remove old field)
- Modify: `backend/devices/admin.py` (remove DeviceHeader references)
- Modify: `backend/devices/urls_html.py` (remove header-form URL)
- Test: update all existing tests

**Step 1: Create data migration**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py makemigrations devices --empty -n migrate_to_config_gather`

Write the migration:

```python
from django.db import migrations


def migrate_endpoints_to_config_gather(apps, schema_editor):
    Device = apps.get_model("devices", "Device")
    DeviceHeader = apps.get_model("devices", "DeviceHeader")
    ConfigGather = apps.get_model("devices", "ConfigGather")
    SiteSettings = apps.get_model("settings", "SiteSettings")

    # Migrate devices with explicit api_endpoint
    for device in Device.objects.exclude(api_endpoint=""):
        headers = {h.key: h.value for h in DeviceHeader.objects.filter(device=device)}
        cg = ConfigGather.objects.create(
            name=f"Migrated: {device.name}",
            gather_type="http",
            config={
                "url": device.api_endpoint,
                "method": "GET",
                "headers": headers,
                "timeout": 30,
                "verify_ssl": True,
            },
        )
        device.config_gather = cg
        device.save(update_fields=["config_gather"])

    # Migrate site default
    try:
        site = SiteSettings.objects.get(pk=1)
        if site.default_api_endpoint:
            url = site.default_api_endpoint.rstrip("/") + "/{device_name}"
            cg = ConfigGather.objects.create(
                name="Migrated: Site Default",
                gather_type="http",
                config={
                    "url": url,
                    "method": "GET",
                    "headers": {},
                    "timeout": 30,
                    "verify_ssl": True,
                },
            )
            site.default_config_gather = cg
            site.save(update_fields=["default_config_gather"])
    except SiteSettings.DoesNotExist:
        pass


def reverse_migration(apps, schema_editor):
    pass  # Not reversible


class Migration(migrations.Migration):
    dependencies = [
        ("devices", "<previous_migration>"),  # fill in actual name
        ("settings", "<previous_migration>"),
    ]

    operations = [
        migrations.RunPython(migrate_endpoints_to_config_gather, reverse_migration),
    ]
```

**Step 2: Run the data migration**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py migrate`

**Step 3: Remove old fields from models**

In `backend/devices/models.py`:
- Remove `api_endpoint` from Device
- Remove `effective_api_endpoint` property
- Remove the entire `DeviceHeader` model

In `backend/settings/models.py`:
- Remove `default_api_endpoint` from SiteSettings

**Step 4: Create schema migration to remove old fields**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py makemigrations devices settings -n remove_old_endpoint_fields && python manage.py migrate`

**Step 5: Clean up admin.py**

In `backend/devices/admin.py`:
- Remove `DeviceHeaderInline`
- Remove `DeviceHeader` import
- Remove `inlines = [DeviceHeaderInline]` from DeviceAdmin
- Replace `api_endpoint` with `config_gather` in DeviceAdmin.list_display
- Add ConfigGather admin registration

```python
from .models import ConfigGather, Device, DeviceGroup


@admin.register(ConfigGather)
class ConfigGatherAdmin(admin.ModelAdmin):
    list_display = ["name", "gather_type", "created_at"]
    search_fields = ["name"]
```

**Step 6: Remove header-form URL**

In `backend/devices/urls_html.py`, remove the `header-form/` path.

**Step 7: Update all existing tests**

Go through `backend/devices/tests.py`, `backend/audits/tests.py`, `backend/settings/tests.py`:
- Remove all references to `api_endpoint` kwarg in Device.objects.create — replace with `config_gather` where needed
- Remove all `DeviceHeader` test classes and references
- Remove `effective_api_endpoint` tests — replace with `effective_config_gather` tests (already added in Task 2)
- Update AuditFixtureMixin.create_device to not set api_endpoint
- Update test_connection tests to mock the handler registry instead of requests.get
- Update SiteSettings tests to use `default_config_gather` instead of `default_api_endpoint`

**Step 8: Run full test suite**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest -v`
Expected: All PASS.

**Step 9: Commit**

```bash
git add backend/devices/ backend/settings/ backend/audits/tests.py
git commit -m "feat: migrate data and remove old endpoint fields"
```

---

### Task 8: Final Verification

**Step 1: Run full test suite**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest -v`
Expected: All PASS.

**Step 2: Run migrations check**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py makemigrations --check`
Expected: No changes detected.

**Step 3: Verify the app starts**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py check`
Expected: System check identified no issues.

**Step 4: Commit any remaining changes**

```bash
git add -A
git commit -m "chore: final cleanup for config gather feature"
```
