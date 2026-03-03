# SSH Config Source Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add SSH-based config fetching via netmiko as a new config source type, with a NetmikoDeviceType reference model, per-device prompt overrides, and an async API trigger.

**Architecture:** Builds on the ConfigSource multi-table inheritance design. Creates a new `config_sources` Django app with `ConfigSource` base model, `SshConfigSource` child, and standalone `NetmikoDeviceType` reference table. SSH fetcher uses netmiko's `ConnectHandler`. Config fetches are queued as async Django-Q2 tasks. Credentials are encrypted via `django-encrypted-model-fields`.

**Tech Stack:** Django 5.1, DRF 3.15, netmiko 4.x, django-encrypted-model-fields, Django-Q2, React 19 + TypeScript + TanStack Query + shadcn/ui

**Design doc:** `docs/plans/2026-03-02-ssh-config-source-design.md`

---

### Task 1: Add Dependencies and Create App Skeleton

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/config_sources/__init__.py`
- Create: `backend/config_sources/models.py`
- Create: `backend/config_sources/admin.py`
- Create: `backend/config_sources/apps.py`
- Create: `backend/config_sources/urls.py`
- Create: `backend/config_sources/views.py`
- Create: `backend/config_sources/serializers.py`
- Create: `backend/config_sources/fetchers.py`
- Modify: `backend/config/settings/base.py`

**Step 1: Add dependencies to requirements.txt**

Add these two lines to `backend/requirements.txt`:

```
netmiko>=4.0,<5.0
django-encrypted-model-fields>=0.6,<1.0
```

**Step 2: Create the config_sources app skeleton**

Create `backend/config_sources/__init__.py` (empty file).

Create `backend/config_sources/apps.py`:

```python
from django.apps import AppConfig


class ConfigSourcesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "config_sources"
```

Create `backend/config_sources/models.py`:

```python
from django.db import models
```

Create `backend/config_sources/admin.py`:

```python
from django.contrib import admin
```

Create `backend/config_sources/urls.py`:

```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

urlpatterns = [
    path("", include(router.urls)),
]
```

Create `backend/config_sources/views.py`:

```python
from rest_framework import viewsets
```

Create `backend/config_sources/serializers.py`:

```python
from rest_framework import serializers
```

Create `backend/config_sources/fetchers.py`:

```python
"""Config source fetch dispatch and transport implementations."""
```

**Step 3: Register the app in settings and urls**

In `backend/config/settings/base.py`, add `"config_sources"` to `INSTALLED_APPS` after `"settings"`:

```python
    # Local apps
    "accounts",
    "devices",
    "rules",
    "audits",
    "common",
    "settings",
    "config_sources",
```

Also add the `FIELD_ENCRYPTION_KEY` setting at the bottom of `base.py`:

```python
# django-encrypted-model-fields
import os as _os
FIELD_ENCRYPTION_KEY = _os.environ.get(
    "FIELD_ENCRYPTION_KEY",
    SECRET_KEY[:32].ljust(32, "x"),  # dev fallback derived from SECRET_KEY
)
```

In `backend/config/urls.py`, add the config_sources URL include:

```python
    path("api/v1/", include("config_sources.urls")),
```

**Step 4: Install new dependencies**

Run: `cd backend && pip install -r requirements.txt`
Expected: Successfully installed netmiko, paramiko, django-encrypted-model-fields and their dependencies.

**Step 5: Verify Django starts**

Run: `cd backend && python manage.py check`
Expected: System check identified no issues.

**Step 6: Commit**

```bash
git add backend/requirements.txt backend/config_sources/ backend/config/settings/base.py backend/config/urls.py
git commit -m "feat: add config_sources app skeleton with netmiko dependency"
```

---

### Task 2: NetmikoDeviceType Model

**Files:**
- Modify: `backend/config_sources/models.py`
- Create: `backend/config_sources/test_models.py`
- Modify: `backend/config_sources/admin.py`

**Step 1: Write the failing test**

Create `backend/config_sources/test_models.py`:

```python
from django.db import IntegrityError
from django.test import TestCase

from config_sources.models import NetmikoDeviceType


class NetmikoDeviceTypeTests(TestCase):
    def test_create_device_type(self):
        ndt = NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
            description="Cisco IOS and IOS-XE devices",
        )
        self.assertEqual(ndt.name, "Cisco IOS")
        self.assertEqual(ndt.driver, "cisco_ios")
        self.assertEqual(ndt.default_command, "show running-config")
        self.assertIsNotNone(ndt.created_at)
        self.assertIsNotNone(ndt.updated_at)

    def test_name_is_unique(self):
        NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
        )
        with self.assertRaises(IntegrityError):
            NetmikoDeviceType.objects.create(
                name="Cisco IOS",
                driver="cisco_ios_xe",
                default_command="show running-config",
            )

    def test_str_returns_name(self):
        ndt = NetmikoDeviceType.objects.create(
            name="Juniper Junos",
            driver="juniper_junos",
            default_command="show configuration",
        )
        self.assertEqual(str(ndt), "Juniper Junos")

    def test_ordering_by_name(self):
        NetmikoDeviceType.objects.create(
            name="Cisco NXOS", driver="cisco_nxos", default_command="show running-config",
        )
        NetmikoDeviceType.objects.create(
            name="Arista EOS", driver="arista_eos", default_command="show running-config",
        )
        names = list(NetmikoDeviceType.objects.values_list("name", flat=True))
        self.assertEqual(names, ["Arista EOS", "Cisco NXOS"])

    def test_description_blank_allowed(self):
        ndt = NetmikoDeviceType.objects.create(
            name="HP ProCurve",
            driver="hp_procurve",
            default_command="show running-config",
        )
        self.assertEqual(ndt.description, "")
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest config_sources/test_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'NetmikoDeviceType'`

**Step 3: Implement the model**

Update `backend/config_sources/models.py`:

```python
from django.db import models


class NetmikoDeviceType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    driver = models.CharField(max_length=100)
    default_command = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
```

**Step 4: Create migration and run tests**

Run: `cd backend && python manage.py makemigrations config_sources`
Expected: Creates `0001_initial.py` with `CreateModel` for `NetmikoDeviceType`.

Run: `cd backend && python -m pytest config_sources/test_models.py -v`
Expected: All 5 tests PASS.

**Step 5: Register in admin**

Update `backend/config_sources/admin.py`:

```python
from django.contrib import admin

from .models import NetmikoDeviceType


@admin.register(NetmikoDeviceType)
class NetmikoDeviceTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "driver", "default_command", "created_at"]
    search_fields = ["name", "driver"]
```

**Step 6: Commit**

```bash
git add backend/config_sources/
git commit -m "feat: add NetmikoDeviceType model with tests"
```

---

### Task 3: ConfigSource Base Model and SshConfigSource Child Model

**Files:**
- Modify: `backend/config_sources/models.py`
- Modify: `backend/config_sources/test_models.py`
- Modify: `backend/config_sources/admin.py`

**Step 1: Write the failing tests**

Add to `backend/config_sources/test_models.py`:

```python
from config_sources.models import ConfigSource, NetmikoDeviceType, SshConfigSource


class ConfigSourceTests(TestCase):
    def test_create_config_source_directly(self):
        """ConfigSource base can be created with source_type."""
        cs = ConfigSource.objects.create(source_type="ssh")
        self.assertEqual(cs.source_type, "ssh")
        self.assertIsNotNone(cs.created_at)

    def test_source_type_choices(self):
        field = ConfigSource._meta.get_field("source_type")
        type_values = [choice[0] for choice in field.choices]
        self.assertIn("api", type_values)
        self.assertIn("git", type_values)
        self.assertIn("manual", type_values)
        self.assertIn("ssh", type_values)


class SshConfigSourceTests(TestCase):
    def setUp(self):
        self.ndt = NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
        )

    def test_create_ssh_source(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            hostname="10.0.0.1",
            port=22,
            username="admin",
            password="secret123",
            timeout=30,
        )
        self.assertEqual(ssh.source_type, "ssh")
        self.assertEqual(ssh.netmiko_device_type, self.ndt)
        self.assertEqual(ssh.hostname, "10.0.0.1")
        self.assertEqual(ssh.port, 22)
        self.assertEqual(ssh.username, "admin")
        self.assertEqual(ssh.password, "secret123")
        self.assertEqual(ssh.timeout, 30)

    def test_ssh_source_inherits_from_config_source(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            username="admin",
        )
        self.assertIsInstance(ssh, ConfigSource)
        cs = ConfigSource.objects.get(pk=ssh.pk)
        self.assertEqual(cs.source_type, "ssh")

    def test_ssh_key_blank_by_default(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            username="admin",
        )
        self.assertEqual(ssh.ssh_key, "")

    def test_command_override_blank_by_default(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            username="admin",
        )
        self.assertEqual(ssh.command_override, "")

    def test_prompt_overrides_default_empty_dict(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            username="admin",
        )
        self.assertEqual(ssh.prompt_overrides, {})

    def test_prompt_overrides_stored(self):
        overrides = {"expect_string": "router#", "read_timeout": 60}
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            username="admin",
            prompt_overrides=overrides,
        )
        ssh.refresh_from_db()
        self.assertEqual(ssh.prompt_overrides, overrides)

    def test_hostname_blank_by_default(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            username="admin",
        )
        self.assertEqual(ssh.hostname, "")

    def test_default_port_is_22(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            username="admin",
        )
        self.assertEqual(ssh.port, 22)

    def test_delete_netmiko_device_type_blocked(self):
        """PROTECT should prevent deleting a NetmikoDeviceType that's in use."""
        SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            username="admin",
        )
        with self.assertRaises(models.ProtectedError):
            self.ndt.delete()

    def test_password_field_is_encrypted(self):
        """Verify the password field uses encryption."""
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            username="admin",
            password="plaintext_secret",
        )
        ssh.refresh_from_db()
        # After refresh, the decrypted value should match
        self.assertEqual(ssh.password, "plaintext_secret")
```

Also update the imports at the top of the test file.

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest config_sources/test_models.py -v -k "ConfigSource or SshConfigSource"`
Expected: FAIL — `ImportError: cannot import name 'ConfigSource'`

**Step 3: Implement the models**

Update `backend/config_sources/models.py`:

```python
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField, EncryptedTextField


class NetmikoDeviceType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    driver = models.CharField(max_length=100)
    default_command = models.CharField(max_length=500)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ConfigSource(models.Model):
    SOURCE_TYPES = [
        ("api", "API Endpoint"),
        ("git", "Git Repository"),
        ("manual", "Manual"),
        ("ssh", "SSH (Netmiko)"),
    ]

    source_type = models.CharField(max_length=50, choices=SOURCE_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"ConfigSource({self.source_type}, pk={self.pk})"


class SshConfigSource(ConfigSource):
    netmiko_device_type = models.ForeignKey(
        NetmikoDeviceType, on_delete=models.PROTECT
    )
    hostname = models.CharField(max_length=255, blank=True, default="")
    port = models.IntegerField(default=22)
    username = EncryptedCharField(max_length=255)
    password = EncryptedCharField(max_length=255, blank=True, default="")
    ssh_key = EncryptedTextField(blank=True, default="")
    command_override = models.CharField(max_length=500, blank=True, default="")
    prompt_overrides = models.JSONField(default=dict, blank=True)
    timeout = models.IntegerField(default=30)

    def __str__(self):
        target = self.hostname or "(device hostname)"
        return f"SSH: {self.username}@{target} via {self.netmiko_device_type.driver}"
```

**Step 4: Create migration and run tests**

Run: `cd backend && python manage.py makemigrations config_sources`
Expected: Creates migration with `CreateModel` for `ConfigSource` and `SshConfigSource`.

Run: `cd backend && python -m pytest config_sources/test_models.py -v`
Expected: All tests PASS.

**Step 5: Register SshConfigSource in admin**

Update `backend/config_sources/admin.py`:

```python
from django.contrib import admin

from .models import NetmikoDeviceType, SshConfigSource


@admin.register(NetmikoDeviceType)
class NetmikoDeviceTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "driver", "default_command", "created_at"]
    search_fields = ["name", "driver"]


@admin.register(SshConfigSource)
class SshConfigSourceAdmin(admin.ModelAdmin):
    list_display = ["netmiko_device_type", "hostname", "username", "port", "created_at"]
    search_fields = ["hostname", "username"]
```

**Step 6: Commit**

```bash
git add backend/config_sources/
git commit -m "feat: add ConfigSource base and SshConfigSource models"
```

---

### Task 4: Device Model Changes

**Files:**
- Modify: `backend/devices/models.py`
- Modify: `backend/config_sources/test_models.py`

**Step 1: Write the failing tests**

Add to `backend/config_sources/test_models.py`:

```python
from devices.models import Device
from config_sources.models import ConfigSource, SshConfigSource, NetmikoDeviceType


class DeviceConfigSourceTests(TestCase):
    def setUp(self):
        self.ndt = NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
        )
        self.device = Device.objects.create(
            name="router-1",
            hostname="10.0.0.1",
        )

    def test_device_config_source_nullable(self):
        """Device.config_source should be None by default."""
        self.assertIsNone(self.device.config_source)

    def test_device_can_link_to_ssh_source(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            username="admin",
        )
        self.device.config_source = ssh.configsource_ptr
        self.device.save()
        self.device.refresh_from_db()
        self.assertEqual(self.device.config_source_id, ssh.pk)

    def test_last_fetched_config_blank_by_default(self):
        self.assertEqual(self.device.last_fetched_config, "")

    def test_config_fetched_at_null_by_default(self):
        self.assertIsNone(self.device.config_fetched_at)

    def test_delete_config_source_sets_null(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            username="admin",
        )
        self.device.config_source = ssh.configsource_ptr
        self.device.save()
        ssh.configsource_ptr.delete()
        self.device.refresh_from_db()
        self.assertIsNone(self.device.config_source)
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest config_sources/test_models.py::DeviceConfigSourceTests -v`
Expected: FAIL — `AttributeError: 'Device' object has no attribute 'config_source'`

**Step 3: Add fields to Device model**

Update `backend/devices/models.py`:

```python
from django.db import models


class DeviceGroup(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Device(models.Model):
    name = models.CharField(max_length=255, unique=True)
    hostname = models.CharField(max_length=255)
    api_endpoint = models.URLField(blank=True, default="")
    enabled = models.BooleanField(default=True)
    groups = models.ManyToManyField(
        "DeviceGroup",
        related_name="devices",
        blank=True,
    )
    config_source = models.OneToOneField(
        "config_sources.ConfigSource",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="device",
    )
    last_fetched_config = models.TextField(blank=True, default="")
    config_fetched_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

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


class DeviceHeader(models.Model):
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="headers",
    )
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=1024)

    class Meta:
        unique_together = [("device", "key")]

    def __str__(self):
        return f"{self.key}: {self.value}"
```

**Step 4: Create migration and run tests**

Run: `cd backend && python manage.py makemigrations devices`
Expected: Creates migration adding `config_source`, `last_fetched_config`, `config_fetched_at` to Device.

Run: `cd backend && python -m pytest config_sources/test_models.py -v`
Expected: All tests PASS.

**Step 5: Verify existing tests still pass**

Run: `cd backend && python -m pytest audits/test_services.py -v`
Expected: All existing tests still PASS (new fields are nullable/blank so don't affect existing tests).

**Step 6: Commit**

```bash
git add backend/devices/models.py backend/devices/migrations/ backend/config_sources/test_models.py
git commit -m "feat: add config_source, last_fetched_config, config_fetched_at to Device"
```

---

### Task 5: SSH Fetcher

**Files:**
- Modify: `backend/config_sources/fetchers.py`
- Create: `backend/config_sources/test_fetchers.py`

**Step 1: Write the failing tests**

Create `backend/config_sources/test_fetchers.py`:

```python
import tempfile
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from config_sources.fetchers import fetch_config, _fetch_ssh
from config_sources.models import NetmikoDeviceType, SshConfigSource
from devices.models import Device


class FetchSshTests(TestCase):
    def setUp(self):
        self.ndt = NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
        )
        self.ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            hostname="10.0.0.1",
            port=22,
            username="admin",
            password="secret",
            timeout=30,
        )
        self.device = Device.objects.create(
            name="router-1",
            hostname="10.0.0.1",
            config_source=self.ssh.configsource_ptr,
        )

    @patch("config_sources.fetchers.ConnectHandler")
    def test_fetch_ssh_returns_command_output(self, mock_handler_cls):
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "hostname router-1\ninterface Gig0/0"
        mock_handler_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_handler_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = _fetch_ssh(self.ssh, self.device)
        self.assertEqual(result, "hostname router-1\ninterface Gig0/0")

    @patch("config_sources.fetchers.ConnectHandler")
    def test_fetch_ssh_uses_correct_connect_params(self, mock_handler_cls):
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "config output"
        mock_handler_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_handler_cls.return_value.__exit__ = MagicMock(return_value=False)

        _fetch_ssh(self.ssh, self.device)

        mock_handler_cls.assert_called_once_with(
            device_type="cisco_ios",
            host="10.0.0.1",
            port=22,
            username="admin",
            password="secret",
            timeout=30,
        )

    @patch("config_sources.fetchers.ConnectHandler")
    def test_fetch_ssh_uses_default_command(self, mock_handler_cls):
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "output"
        mock_handler_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_handler_cls.return_value.__exit__ = MagicMock(return_value=False)

        _fetch_ssh(self.ssh, self.device)
        mock_conn.send_command.assert_called_once_with("show running-config")

    @patch("config_sources.fetchers.ConnectHandler")
    def test_fetch_ssh_uses_command_override(self, mock_handler_cls):
        self.ssh.command_override = "display current-configuration"
        self.ssh.save()

        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "output"
        mock_handler_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_handler_cls.return_value.__exit__ = MagicMock(return_value=False)

        _fetch_ssh(self.ssh, self.device)
        mock_conn.send_command.assert_called_once_with("display current-configuration")

    @patch("config_sources.fetchers.ConnectHandler")
    def test_fetch_ssh_passes_prompt_overrides(self, mock_handler_cls):
        self.ssh.prompt_overrides = {"expect_string": "router#", "read_timeout": 60}
        self.ssh.save()

        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "output"
        mock_handler_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_handler_cls.return_value.__exit__ = MagicMock(return_value=False)

        _fetch_ssh(self.ssh, self.device)
        mock_conn.send_command.assert_called_once_with(
            "show running-config",
            expect_string="router#",
            read_timeout=60,
        )

    @patch("config_sources.fetchers.ConnectHandler")
    def test_fetch_ssh_falls_back_to_device_hostname(self, mock_handler_cls):
        self.ssh.hostname = ""
        self.ssh.save()
        self.device.hostname = "192.168.1.1"
        self.device.save()

        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "output"
        mock_handler_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_handler_cls.return_value.__exit__ = MagicMock(return_value=False)

        _fetch_ssh(self.ssh, self.device)
        call_kwargs = mock_handler_cls.call_args[1]
        self.assertEqual(call_kwargs["host"], "192.168.1.1")


class FetchConfigDispatchTests(TestCase):
    def setUp(self):
        self.ndt = NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
        )

    def test_fetch_config_no_source_raises(self):
        device = Device.objects.create(name="no-source", hostname="10.0.0.1")
        with self.assertRaises(ValueError) as ctx:
            fetch_config(device)
        self.assertIn("no config source", str(ctx.exception).lower())

    @patch("config_sources.fetchers._fetch_ssh")
    def test_fetch_config_dispatches_ssh(self, mock_fetch_ssh):
        mock_fetch_ssh.return_value = "config text"
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            username="admin",
        )
        device = Device.objects.create(
            name="ssh-device",
            hostname="10.0.0.1",
            config_source=ssh.configsource_ptr,
        )

        result = fetch_config(device)
        self.assertEqual(result, "config text")
        mock_fetch_ssh.assert_called_once()

    @patch("config_sources.fetchers._fetch_ssh")
    def test_fetch_config_updates_device_fields(self, mock_fetch_ssh):
        mock_fetch_ssh.return_value = "fetched config"
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            username="admin",
        )
        device = Device.objects.create(
            name="update-device",
            hostname="10.0.0.1",
            config_source=ssh.configsource_ptr,
        )

        fetch_config(device)
        device.refresh_from_db()
        self.assertEqual(device.last_fetched_config, "fetched config")
        self.assertIsNotNone(device.config_fetched_at)
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest config_sources/test_fetchers.py -v`
Expected: FAIL — `ImportError: cannot import name 'fetch_config'`

**Step 3: Implement the fetcher**

Update `backend/config_sources/fetchers.py`:

```python
"""Config source fetch dispatch and transport implementations."""

import logging
import os
import stat
import tempfile

from django.utils import timezone
from netmiko import ConnectHandler

logger = logging.getLogger(__name__)


def fetch_config(device):
    """Fetch config for a device from its configured source.

    Dispatches to the appropriate transport handler based on source_type.
    Updates device.last_fetched_config and device.config_fetched_at.

    Returns the config text.
    """
    source = device.config_source
    if source is None:
        raise ValueError(
            f"Device '{device.name}' has no config source configured"
        )

    match source.source_type:
        case "ssh":
            text = _fetch_ssh(source.sshconfigsource, device)
        case _:
            raise ValueError(
                f"Unsupported config source type: {source.source_type}"
            )

    device.last_fetched_config = text
    device.config_fetched_at = timezone.now()
    device.save(update_fields=["last_fetched_config", "config_fetched_at"])
    return text


def _fetch_ssh(ssh_source, device):
    """Connect via netmiko and run the config dump command."""
    ndt = ssh_source.netmiko_device_type
    command = ssh_source.command_override or ndt.default_command

    connect_params = {
        "device_type": ndt.driver,
        "host": ssh_source.hostname or device.hostname,
        "port": ssh_source.port,
        "username": ssh_source.username,
        "password": ssh_source.password,
        "timeout": ssh_source.timeout,
    }

    key_path = None
    if ssh_source.ssh_key:
        key_path = _write_temp_key(ssh_source.ssh_key)
        connect_params["use_keys"] = True
        connect_params["key_file"] = key_path

    try:
        with ConnectHandler(**connect_params) as conn:
            send_kwargs = {}
            if ssh_source.prompt_overrides:
                send_kwargs.update(ssh_source.prompt_overrides)
            output = conn.send_command(command, **send_kwargs)
        return output
    finally:
        if key_path:
            _cleanup_temp_key(key_path)


def _write_temp_key(key_text):
    """Write SSH key to a temp file with restrictive permissions."""
    fd, path = tempfile.mkstemp(prefix="netaudit_ssh_", suffix=".key")
    try:
        os.write(fd, key_text.encode())
    finally:
        os.close(fd)
    os.chmod(path, stat.S_IRUSR)
    return path


def _cleanup_temp_key(path):
    """Remove a temporary SSH key file."""
    try:
        os.unlink(path)
    except OSError:
        logger.warning("Failed to clean up temp SSH key: %s", path)
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest config_sources/test_fetchers.py -v`
Expected: All tests PASS.

**Step 5: Commit**

```bash
git add backend/config_sources/fetchers.py backend/config_sources/test_fetchers.py
git commit -m "feat: add SSH fetcher with netmiko transport and dispatch"
```

---

### Task 6: NetmikoDeviceType API (Serializer, ViewSet, URLs)

**Files:**
- Modify: `backend/config_sources/serializers.py`
- Modify: `backend/config_sources/views.py`
- Modify: `backend/config_sources/urls.py`
- Create: `backend/config_sources/test_api.py`

**Step 1: Write the failing tests**

Create `backend/config_sources/test_api.py`:

```python
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from config_sources.models import NetmikoDeviceType


class NetmikoDeviceTypeAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testadmin",
            password="testpass123",
            role="admin",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_list_device_types(self):
        NetmikoDeviceType.objects.create(
            name="Cisco IOS", driver="cisco_ios", default_command="show running-config",
        )
        response = self.client.get("/api/v1/netmiko-device-types/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Cisco IOS")

    def test_create_device_type(self):
        data = {
            "name": "Arista EOS",
            "driver": "arista_eos",
            "default_command": "show running-config",
            "description": "Arista switches",
        }
        response = self.client.post("/api/v1/netmiko-device-types/", data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Arista EOS")
        self.assertEqual(response.data["driver"], "arista_eos")
        self.assertTrue(NetmikoDeviceType.objects.filter(name="Arista EOS").exists())

    def test_retrieve_device_type(self):
        ndt = NetmikoDeviceType.objects.create(
            name="Juniper Junos", driver="juniper_junos", default_command="show configuration",
        )
        response = self.client.get(f"/api/v1/netmiko-device-types/{ndt.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Juniper Junos")

    def test_update_device_type(self):
        ndt = NetmikoDeviceType.objects.create(
            name="Cisco NXOS", driver="cisco_nxos", default_command="show running-config",
        )
        response = self.client.put(
            f"/api/v1/netmiko-device-types/{ndt.id}/",
            {"name": "Cisco NXOS", "driver": "cisco_nxos", "default_command": "show run"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        ndt.refresh_from_db()
        self.assertEqual(ndt.default_command, "show run")

    def test_delete_device_type(self):
        ndt = NetmikoDeviceType.objects.create(
            name="HP ProCurve", driver="hp_procurve", default_command="show running-config",
        )
        response = self.client.delete(f"/api/v1/netmiko-device-types/{ndt.id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(NetmikoDeviceType.objects.filter(pk=ndt.id).exists())

    def test_viewer_can_list(self):
        viewer = User.objects.create_user(
            username="viewer", password="pass", role="viewer",
        )
        client = APIClient()
        client.force_authenticate(user=viewer)
        response = client.get("/api/v1/netmiko-device-types/")
        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_create(self):
        viewer = User.objects.create_user(
            username="viewer", password="pass", role="viewer",
        )
        client = APIClient()
        client.force_authenticate(user=viewer)
        response = client.post(
            "/api/v1/netmiko-device-types/",
            {"name": "Test", "driver": "test", "default_command": "test"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest config_sources/test_api.py -v`
Expected: FAIL — 404 or ImportError

**Step 3: Implement serializer, viewset, and URLs**

Update `backend/config_sources/serializers.py`:

```python
from rest_framework import serializers

from .models import NetmikoDeviceType


class NetmikoDeviceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetmikoDeviceType
        fields = [
            "id",
            "name",
            "driver",
            "default_command",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
```

Update `backend/config_sources/views.py`:

```python
from rest_framework import viewsets

from accounts.permissions import IsEditorOrAbove, IsViewerOrAbove

from .models import NetmikoDeviceType
from .serializers import NetmikoDeviceTypeSerializer


class NetmikoDeviceTypeViewSet(viewsets.ModelViewSet):
    queryset = NetmikoDeviceType.objects.all()
    serializer_class = NetmikoDeviceTypeSerializer
    search_fields = ["name", "driver"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]
```

Update `backend/config_sources/urls.py`:

```python
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import NetmikoDeviceTypeViewSet

router = DefaultRouter()
router.register("netmiko-device-types", NetmikoDeviceTypeViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest config_sources/test_api.py -v`
Expected: All tests PASS.

**Step 5: Commit**

```bash
git add backend/config_sources/serializers.py backend/config_sources/views.py backend/config_sources/urls.py backend/config_sources/test_api.py
git commit -m "feat: add NetmikoDeviceType REST API with permissions"
```

---

### Task 7: SshConfigSource Serializer and Device Serializer Updates

**Files:**
- Modify: `backend/config_sources/serializers.py`
- Modify: `backend/devices/serializers.py`
- Modify: `backend/config_sources/test_api.py`

**Step 1: Write the failing tests**

Add to `backend/config_sources/test_api.py`:

```python
from config_sources.models import NetmikoDeviceType, SshConfigSource
from devices.models import Device


class DeviceWithSshConfigSourceAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testadmin", password="testpass123", role="admin",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.ndt = NetmikoDeviceType.objects.create(
            name="Cisco IOS", driver="cisco_ios", default_command="show running-config",
        )

    def test_create_device_with_ssh_source(self):
        data = {
            "name": "router-1",
            "hostname": "10.0.0.1",
            "enabled": True,
            "headers": [],
            "groups": [],
            "config_source": {
                "source_type": "ssh",
                "netmiko_device_type": self.ndt.id,
                "hostname": "10.0.0.1",
                "port": 22,
                "username": "admin",
                "password": "secret",
                "timeout": 30,
            },
        }
        response = self.client.post("/api/v1/devices/", data, format="json")
        self.assertEqual(response.status_code, 201)
        device = Device.objects.get(name="router-1")
        self.assertIsNotNone(device.config_source)
        ssh = device.config_source.sshconfigsource
        self.assertEqual(ssh.username, "admin")
        self.assertEqual(ssh.netmiko_device_type_id, self.ndt.id)

    def test_create_device_without_config_source(self):
        data = {
            "name": "router-2",
            "hostname": "10.0.0.2",
            "enabled": True,
            "headers": [],
            "groups": [],
        }
        response = self.client.post("/api/v1/devices/", data, format="json")
        self.assertEqual(response.status_code, 201)
        device = Device.objects.get(name="router-2")
        self.assertIsNone(device.config_source)

    def test_device_response_includes_config_source(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            hostname="10.0.0.1",
            username="admin",
            password="secret",
        )
        device = Device.objects.create(
            name="router-3",
            hostname="10.0.0.1",
            config_source=ssh.configsource_ptr,
        )
        response = self.client.get(f"/api/v1/devices/{device.id}/")
        self.assertEqual(response.status_code, 200)
        cs = response.data["config_source"]
        self.assertEqual(cs["source_type"], "ssh")
        self.assertEqual(cs["netmiko_device_type"], self.ndt.id)
        # Password should not be returned in response
        self.assertNotIn("password", cs)

    def test_update_device_config_source(self):
        device = Device.objects.create(
            name="router-4", hostname="10.0.0.1",
        )
        data = {
            "name": "router-4",
            "hostname": "10.0.0.1",
            "enabled": True,
            "headers": [],
            "groups": [],
            "config_source": {
                "source_type": "ssh",
                "netmiko_device_type": self.ndt.id,
                "username": "newadmin",
                "password": "newpass",
            },
        }
        response = self.client.put(f"/api/v1/devices/{device.id}/", data, format="json")
        self.assertEqual(response.status_code, 200)
        device.refresh_from_db()
        self.assertIsNotNone(device.config_source)
        ssh = device.config_source.sshconfigsource
        self.assertEqual(ssh.username, "newadmin")

    def test_remove_config_source_by_setting_null(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            username="admin",
        )
        device = Device.objects.create(
            name="router-5", hostname="10.0.0.1",
            config_source=ssh.configsource_ptr,
        )
        data = {
            "name": "router-5",
            "hostname": "10.0.0.1",
            "enabled": True,
            "headers": [],
            "groups": [],
            "config_source": None,
        }
        response = self.client.put(f"/api/v1/devices/{device.id}/", data, format="json")
        self.assertEqual(response.status_code, 200)
        device.refresh_from_db()
        self.assertIsNone(device.config_source)

    def test_device_includes_last_fetched_config(self):
        device = Device.objects.create(
            name="router-6", hostname="10.0.0.1",
            last_fetched_config="hostname router-6",
        )
        response = self.client.get(f"/api/v1/devices/{device.id}/")
        self.assertEqual(response.data["last_fetched_config"], "hostname router-6")

    def test_create_ssh_source_with_prompt_overrides(self):
        data = {
            "name": "router-7",
            "hostname": "10.0.0.1",
            "enabled": True,
            "headers": [],
            "groups": [],
            "config_source": {
                "source_type": "ssh",
                "netmiko_device_type": self.ndt.id,
                "username": "admin",
                "password": "secret",
                "prompt_overrides": {"expect_string": "router#"},
            },
        }
        response = self.client.post("/api/v1/devices/", data, format="json")
        self.assertEqual(response.status_code, 201)
        device = Device.objects.get(name="router-7")
        ssh = device.config_source.sshconfigsource
        self.assertEqual(ssh.prompt_overrides, {"expect_string": "router#"})
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest config_sources/test_api.py::DeviceWithSshConfigSourceAPITests -v`
Expected: FAIL — field not present in serializer

**Step 3: Implement SshConfigSource serializer**

Update `backend/config_sources/serializers.py`:

```python
from rest_framework import serializers

from .models import ConfigSource, NetmikoDeviceType, SshConfigSource


class NetmikoDeviceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NetmikoDeviceType
        fields = [
            "id",
            "name",
            "driver",
            "default_command",
            "description",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class SshConfigSourceSerializer(serializers.ModelSerializer):
    source_type = serializers.CharField(default="ssh")

    class Meta:
        model = SshConfigSource
        fields = [
            "source_type",
            "netmiko_device_type",
            "hostname",
            "port",
            "username",
            "password",
            "ssh_key",
            "command_override",
            "prompt_overrides",
            "timeout",
        ]
        extra_kwargs = {
            "password": {"write_only": True, "required": False},
            "ssh_key": {"write_only": True, "required": False},
            "hostname": {"required": False},
            "port": {"required": False},
            "command_override": {"required": False},
            "prompt_overrides": {"required": False},
            "timeout": {"required": False},
        }


class ConfigSourceField(serializers.Field):
    """Polymorphic serializer field for config sources.

    On read: returns source data based on source_type.
    On write: accepts dict with source_type to create/replace the source.
    """

    def to_representation(self, value):
        if value is None:
            return None
        if value.source_type == "ssh":
            ssh = value.sshconfigsource
            return {
                "source_type": "ssh",
                "netmiko_device_type": ssh.netmiko_device_type_id,
                "hostname": ssh.hostname,
                "port": ssh.port,
                "username": ssh.username,
                "command_override": ssh.command_override,
                "prompt_overrides": ssh.prompt_overrides,
                "timeout": ssh.timeout,
            }
        return {"source_type": value.source_type}

    def to_internal_value(self, data):
        if data is None:
            return None
        if not isinstance(data, dict):
            raise serializers.ValidationError("Expected a dict or null.")
        source_type = data.get("source_type")
        if source_type == "ssh":
            serializer = SshConfigSourceSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            return serializer.validated_data
        raise serializers.ValidationError(f"Unsupported source_type: {source_type}")
```

**Step 4: Update Device serializer**

Update `backend/devices/serializers.py`:

```python
from rest_framework import serializers

from config_sources.models import SshConfigSource
from config_sources.serializers import ConfigSourceField

from .models import Device, DeviceGroup, DeviceHeader


class DeviceHeaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceHeader
        fields = ["id", "key", "value"]


class DeviceGroupSerializer(serializers.ModelSerializer):
    device_count = serializers.IntegerField(source="devices.count", read_only=True)
    devices = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Device.objects.all(), required=False,
    )

    class Meta:
        model = DeviceGroup
        fields = [
            "id",
            "name",
            "description",
            "devices",
            "device_count",
            "created_at",
            "updated_at",
        ]


class DeviceSerializer(serializers.ModelSerializer):
    headers = DeviceHeaderSerializer(many=True, required=False)
    groups = serializers.PrimaryKeyRelatedField(
        many=True, queryset=DeviceGroup.objects.all(), required=False,
    )
    effective_api_endpoint = serializers.CharField(read_only=True)
    config_source = ConfigSourceField(required=False, allow_null=True)
    last_fetched_config = serializers.CharField(read_only=True)
    config_fetched_at = serializers.DateTimeField(read_only=True)

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
            "groups",
            "config_source",
            "last_fetched_config",
            "config_fetched_at",
            "created_at",
            "updated_at",
        ]

    def _handle_config_source(self, instance, config_source_data):
        """Create or replace config source on a device."""
        # Remove old source if exists
        if instance.config_source:
            old_source = instance.config_source
            instance.config_source = None
            instance.save(update_fields=["config_source"])
            # Delete the child first, then the base
            if old_source.source_type == "ssh":
                old_source.sshconfigsource.delete()
            old_source.delete()

        if config_source_data is None:
            return

        source_type = config_source_data.pop("source_type", None)
        if source_type == "ssh":
            ssh = SshConfigSource.objects.create(
                source_type="ssh", **config_source_data
            )
            instance.config_source = ssh.configsource_ptr
            instance.save(update_fields=["config_source"])

    def create(self, validated_data):
        headers_data = validated_data.pop("headers", [])
        groups_data = validated_data.pop("groups", [])
        config_source_data = validated_data.pop("config_source", None)
        device = Device.objects.create(**validated_data)
        for header_data in headers_data:
            DeviceHeader.objects.create(device=device, **header_data)
        if groups_data:
            device.groups.set(groups_data)
        if config_source_data is not None:
            self._handle_config_source(device, config_source_data)
        return device

    def update(self, instance, validated_data):
        headers_data = validated_data.pop("headers", None)
        groups_data = validated_data.pop("groups", None)
        config_source_data = validated_data.pop("config_source", "UNSET")
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if headers_data is not None:
            instance.headers.all().delete()
            for header_data in headers_data:
                DeviceHeader.objects.create(device=instance, **header_data)

        if groups_data is not None:
            instance.groups.set(groups_data)

        if config_source_data != "UNSET":
            self._handle_config_source(instance, config_source_data)

        return instance
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest config_sources/test_api.py -v`
Expected: All tests PASS.

Run: `cd backend && python -m pytest audits/test_services.py -v`
Expected: Existing tests still PASS.

**Step 5: Commit**

```bash
git add backend/config_sources/serializers.py backend/devices/serializers.py backend/config_sources/test_api.py
git commit -m "feat: add SshConfigSource serializer and nested config_source on Device API"
```

---

### Task 8: Async Fetch-Config Endpoint

**Files:**
- Modify: `backend/devices/views.py`
- Create: `backend/config_sources/tasks.py`
- Modify: `backend/config_sources/test_api.py`

**Step 1: Write the failing tests**

Add to `backend/config_sources/test_api.py`:

```python
from unittest.mock import patch


class FetchConfigAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testadmin", password="testpass123", role="admin",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.ndt = NetmikoDeviceType.objects.create(
            name="Cisco IOS", driver="cisco_ios", default_command="show running-config",
        )

    @patch("devices.views.config_tasks.enqueue_fetch_config")
    def test_fetch_config_queues_task(self, mock_enqueue):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            username="admin",
        )
        device = Device.objects.create(
            name="router-fc", hostname="10.0.0.1",
            config_source=ssh.configsource_ptr,
        )
        response = self.client.post(f"/api/v1/devices/{device.id}/fetch_config/")
        self.assertEqual(response.status_code, 202)
        mock_enqueue.assert_called_once_with(device.id)
        self.assertIn("status", response.data)
        self.assertEqual(response.data["status"], "queued")

    def test_fetch_config_no_source_returns_400(self):
        device = Device.objects.create(
            name="router-no-src", hostname="10.0.0.1",
        )
        response = self.client.post(f"/api/v1/devices/{device.id}/fetch_config/")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.data)
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest config_sources/test_api.py::FetchConfigAPITests -v`
Expected: FAIL

**Step 3: Create the task wrapper**

Create `backend/config_sources/tasks.py`:

```python
"""Django-Q2 task wrappers for config source operations."""

import logging

from django_q.tasks import async_task

logger = logging.getLogger(__name__)


def enqueue_fetch_config(device_id):
    """Queue an async config fetch for a device."""
    async_task(
        "config_sources.tasks.run_fetch_config",
        device_id,
    )


def run_fetch_config(device_id):
    """Execute a config fetch for a device (runs in Q2 worker)."""
    from devices.models import Device

    from .fetchers import fetch_config

    device = Device.objects.get(pk=device_id)
    fetch_config(device)
    logger.info("Config fetched for device %s (id=%d)", device.name, device.id)
```

**Step 4: Update DeviceViewSet.fetch_config**

Update `backend/devices/views.py`:

```python
import requests
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsEditorOrAbove, IsViewerOrAbove
from audits import tasks as audit_tasks
from config_sources import tasks as config_tasks

from .models import Device, DeviceGroup
from .serializers import DeviceGroupSerializer, DeviceSerializer


class DeviceGroupViewSet(viewsets.ModelViewSet):
    queryset = DeviceGroup.objects.prefetch_related("devices").all()
    serializer_class = DeviceGroupSerializer
    search_fields = ["name", "description"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsViewerOrAbove()]
        return [IsEditorOrAbove()]

    @action(detail=True, methods=["post"])
    def run_audit(self, request, pk=None):
        group = self.get_object()
        devices = group.devices.filter(enabled=True)
        for device in devices:
            audit_tasks.enqueue_audit(device.id, trigger="manual")
        return Response({
            "audits_started": devices.count(),
            "group": group.name,
        })


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

    @action(detail=True, methods=["post"])
    def fetch_config(self, request, pk=None):
        device = self.get_object()
        if device.config_source is None:
            return Response(
                {"error": "No config source configured for this device."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        config_tasks.enqueue_fetch_config(device.id)
        return Response(
            {"status": "queued", "device_id": device.id},
            status=status.HTTP_202_ACCEPTED,
        )
```

**Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest config_sources/test_api.py::FetchConfigAPITests -v`
Expected: All tests PASS.

Run: `cd backend && python -m pytest audits/test_services.py -v`
Expected: Existing tests still PASS (the old fetch_config action was GET, now POST — existing tests that don't test the endpoint directly are unaffected).

**Step 6: Commit**

```bash
git add backend/devices/views.py backend/config_sources/tasks.py backend/config_sources/test_api.py
git commit -m "feat: add async fetch-config endpoint via Django-Q2"
```

---

### Task 9: Frontend — NetmikoDeviceType Types and Hooks

**Files:**
- Create: `frontend/src/types/netmiko.ts`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/types/device.ts`
- Create: `frontend/src/hooks/use-netmiko-device-types.ts`

**Step 1: Create TypeScript types**

Create `frontend/src/types/netmiko.ts`:

```typescript
export interface NetmikoDeviceType {
  id: number;
  name: string;
  driver: string;
  default_command: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface NetmikoDeviceTypeFormData {
  name: string;
  driver: string;
  default_command: string;
  description?: string;
}
```

**Step 2: Update device types to include config source**

Update `frontend/src/types/device.ts`:

```typescript
export interface DeviceHeader {
  id?: number;
  key: string;
  value: string;
}

export interface SshConfigSourceData {
  source_type: "ssh";
  netmiko_device_type: number;
  hostname?: string;
  port?: number;
  username: string;
  password?: string;
  ssh_key?: string;
  command_override?: string;
  prompt_overrides?: Record<string, unknown>;
  timeout?: number;
}

export type ConfigSourceData = SshConfigSourceData | null;

export interface ConfigSourceResponse {
  source_type: string;
  netmiko_device_type?: number;
  hostname?: string;
  port?: number;
  username?: string;
  command_override?: string;
  prompt_overrides?: Record<string, unknown>;
  timeout?: number;
}

export interface Device {
  id: number;
  name: string;
  hostname: string;
  api_endpoint: string;
  effective_api_endpoint: string;
  enabled: boolean;
  headers: DeviceHeader[];
  groups: number[];
  config_source: ConfigSourceResponse | null;
  last_fetched_config: string;
  config_fetched_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DeviceGroup {
  id: number;
  name: string;
  description: string;
  devices: number[];
  device_count: number;
  created_at: string;
  updated_at: string;
}

export interface DeviceFormData {
  name: string;
  hostname: string;
  api_endpoint?: string;
  enabled: boolean;
  headers: DeviceHeader[];
  groups: number[];
  config_source?: ConfigSourceData;
}

export interface DeviceGroupFormData {
  name: string;
  description: string;
  devices: number[];
}

export interface TestConnectionResult {
  status_code: number;
  content_length: number;
}
```

**Step 3: Update type index exports**

Read `frontend/src/types/index.ts` first, then add the netmiko exports. Add this line:

```typescript
export type { NetmikoDeviceType, NetmikoDeviceTypeFormData } from "./netmiko";
```

Also export the new config source types:

```typescript
export type { ConfigSourceData, ConfigSourceResponse, SshConfigSourceData } from "./device";
```

**Step 4: Create React Query hooks for NetmikoDeviceType**

Create `frontend/src/hooks/use-netmiko-device-types.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import api from "@/lib/api";
import type { NetmikoDeviceType, NetmikoDeviceTypeFormData, PaginatedResponse } from "@/types";

export function useNetmikoDeviceTypes(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["netmiko-device-types", params],
    queryFn: async () => {
      const response = await api.get<PaginatedResponse<NetmikoDeviceType>>("/netmiko-device-types/", { params });
      return response.data;
    },
  });
}

export function useNetmikoDeviceType(id: number) {
  return useQuery({
    queryKey: ["netmiko-device-types", id],
    queryFn: async () => {
      const response = await api.get<NetmikoDeviceType>(`/netmiko-device-types/${id}/`);
      return response.data;
    },
    enabled: !!id,
  });
}

export function useCreateNetmikoDeviceType() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: NetmikoDeviceTypeFormData) => {
      const response = await api.post<NetmikoDeviceType>("/netmiko-device-types/", data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["netmiko-device-types"] });
      toast.success("Device type created");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useUpdateNetmikoDeviceType(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: NetmikoDeviceTypeFormData) => {
      const response = await api.put<NetmikoDeviceType>(`/netmiko-device-types/${id}/`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["netmiko-device-types"] });
      queryClient.invalidateQueries({ queryKey: ["netmiko-device-types", id] });
      toast.success("Device type updated");
    },
    onError: () => toast.error("Operation failed"),
  });
}

export function useDeleteNetmikoDeviceType() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await api.delete(`/netmiko-device-types/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["netmiko-device-types"] });
      toast.success("Device type deleted");
    },
    onError: () => toast.error("Operation failed"),
  });
}
```

**Step 5: Update useFetchDeviceConfig to use POST**

In `frontend/src/hooks/use-devices.ts`, update `useFetchDeviceConfig`:

```typescript
export function useFetchDeviceConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (deviceId: number) => {
      const response = await api.post<{ status: string; device_id: number }>(`/devices/${deviceId}/fetch_config/`);
      return response.data;
    },
    onSuccess: (_, deviceId) => {
      queryClient.invalidateQueries({ queryKey: ["devices", deviceId] });
      toast.success("Config fetch queued");
    },
    onError: () => toast.error("Failed to trigger config fetch"),
  });
}
```

**Step 6: Verify frontend builds**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors.

**Step 7: Commit**

```bash
git add frontend/src/types/ frontend/src/hooks/use-netmiko-device-types.ts frontend/src/hooks/use-devices.ts
git commit -m "feat: add frontend types and hooks for NetmikoDeviceType and config sources"
```

---

### Task 10: Frontend — NetmikoDeviceType CRUD Pages

**Files:**
- Create: `frontend/src/pages/netmiko-device-types/list.tsx`
- Create: `frontend/src/pages/netmiko-device-types/form.tsx`

**Step 1: Create the list page**

Create `frontend/src/pages/netmiko-device-types/list.tsx` following the pattern in `frontend/src/pages/devices/list.tsx`. Include:
- Table with columns: Name, Driver, Default Command, Created
- New button linking to `/netmiko-device-types/new`
- Edit links to `/netmiko-device-types/:id/edit`
- Delete button with confirmation

Use `useNetmikoDeviceTypes()` hook and the same shadcn Card/Table components as other list pages.

**Step 2: Create the form page**

Create `frontend/src/pages/netmiko-device-types/form.tsx` following the pattern in `frontend/src/pages/devices/form.tsx`. Include:
- Fields: name, driver, default_command, description (textarea)
- Helper text under driver field listing common netmiko drivers (cisco_ios, cisco_nxos, arista_eos, juniper_junos, etc.)
- Back button to list
- Create/Edit mode (use URL params like device form)

Use `useCreateNetmikoDeviceType()` / `useUpdateNetmikoDeviceType()` hooks.

**Step 3: Verify frontend builds**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors.

**Step 4: Commit**

```bash
git add frontend/src/pages/netmiko-device-types/
git commit -m "feat: add NetmikoDeviceType list and form pages"
```

---

### Task 11: Frontend — Device Form SSH Config Source Fields

**Files:**
- Modify: `frontend/src/pages/devices/form.tsx`

**Step 1: Update the device form**

Add SSH config source fields to `frontend/src/pages/devices/form.tsx`:

- Add a "Configuration Source" card after the Headers card
- Source type selector: radio buttons for "None" and "SSH" (other types not implemented yet)
- When SSH is selected, show:
  - Netmiko Device Type dropdown (fetched via `useNetmikoDeviceTypes()`)
  - SSH Hostname (optional, placeholder "Defaults to device hostname")
  - Port (default 22)
  - Username (required)
  - Password (password field)
  - SSH Key (textarea, optional)
  - Command Override (optional)
  - Prompt Overrides (textarea for JSON, optional)
  - Timeout (default 30)
- Include config_source in form submission data
- When editing, populate from device.config_source response

**Step 2: Verify frontend builds**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors.

**Step 3: Commit**

```bash
git add frontend/src/pages/devices/form.tsx
git commit -m "feat: add SSH config source fields to device form"
```

---

### Task 12: Frontend — Routes and Navigation

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/layout/app-header.tsx`

**Step 1: Add routes**

In `frontend/src/App.tsx`, add imports and routes for NetmikoDeviceType pages:

```typescript
import { NetmikoDeviceTypeListPage } from "@/pages/netmiko-device-types/list";
import { NetmikoDeviceTypeFormPage } from "@/pages/netmiko-device-types/form";
```

Add routes inside the `<Route element={<AppLayout />}>` block:

```tsx
<Route path="/netmiko-device-types" element={<NetmikoDeviceTypeListPage />} />
<Route path="/netmiko-device-types/new" element={<NetmikoDeviceTypeFormPage />} />
<Route path="/netmiko-device-types/:id/edit" element={<NetmikoDeviceTypeFormPage />} />
```

**Step 2: Add navigation entry**

In `frontend/src/components/layout/app-header.tsx`, add NetmikoDeviceType to the "Netbox" nav group. Import a suitable icon (e.g., `Terminal` from lucide-react) and add a child entry:

```typescript
{
  label: "Netbox",
  prefixes: ["/devices", "/groups", "/netmiko-device-types"],
  children: [
    { label: "Devices", href: "/devices", icon: Server },
    { label: "Groups", href: "/groups", icon: FolderTree },
    { label: "Device Types", href: "/netmiko-device-types", icon: Terminal },
  ],
},
```

**Step 3: Verify frontend builds**

Run: `cd frontend && npx tsc --noEmit`
Expected: No type errors.

**Step 4: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/layout/app-header.tsx
git commit -m "feat: add NetmikoDeviceType routes and navigation"
```

---

### Task 13: Final Verification

**Step 1: Run all backend tests**

Run: `cd backend && python -m pytest -v`
Expected: All tests PASS.

**Step 2: Run frontend type check**

Run: `cd frontend && npx tsc --noEmit`
Expected: No errors.

**Step 3: Run Django system check**

Run: `cd backend && python manage.py check`
Expected: System check identified no issues.

**Step 4: Verify migrations are clean**

Run: `cd backend && python manage.py makemigrations --check --dry-run`
Expected: No changes detected.

**Step 5: Commit any remaining changes**

If any loose files, commit them.
