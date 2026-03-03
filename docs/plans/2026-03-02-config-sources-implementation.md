# Config Sources Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add flexible device config loading via a strategy pattern — API endpoint, git repo, or manual paste — replacing the current hardcoded API-only approach.

**Architecture:** New `config_sources` Django app using multi-table inheritance (`ConfigSource` base, `ApiConfigSource`, `GitConfigSource`, `ManualConfigSource` children). Device gets a OneToOneField to ConfigSource plus cached config storage. Fetcher dispatch layer routes to the right strategy. Config source data is inline on the device API payload.

**Tech Stack:** Django 5.1, DRF, React 19, TanStack Query, Monaco Editor, shadcn/ui, Tailwind CSS 4, subprocess (git CLI)

**Design doc:** `docs/plans/2026-03-01-config-sources-design.md`

---

### Task 1: Create the `config_sources` Django App

**Files:**
- Create: `backend/config_sources/__init__.py`
- Create: `backend/config_sources/apps.py`
- Create: `backend/config_sources/models.py`
- Create: `backend/config_sources/admin.py`
- Create: `backend/config_sources/tests.py`
- Modify: `backend/config/settings/base.py:39` (add to INSTALLED_APPS)

**Step 1: Scaffold the app**

```bash
cd /Users/aaronroth/Documents/netaudit/backend
python manage.py startapp config_sources
```

**Step 2: Register in settings**

In `backend/config/settings/base.py`, add `"config_sources"` to the local apps section (after line 44, before `"settings"`):

```python
    # Local apps
    "accounts",
    "devices",
    "rules",
    "audits",
    "common",
    "config_sources",
    "settings",
```

**Step 3: Commit**

```bash
git add backend/config_sources/ backend/config/settings/base.py
git commit -m "feat: scaffold config_sources django app"
```

---

### Task 2: Write ConfigSource Base Model + Tests

**Files:**
- Create: `backend/config_sources/models.py`
- Create: `backend/config_sources/tests.py`

**Step 1: Write the failing tests**

Write `backend/config_sources/tests.py`:

```python
from django.test import TestCase

from .models import ConfigSource


class ConfigSourceModelTests(TestCase):
    """Tests for the ConfigSource base model."""

    def test_create_api_source(self):
        source = ConfigSource.objects.create(source_type="api")
        self.assertEqual(source.source_type, "api")
        self.assertIsNotNone(source.created_at)
        self.assertIsNotNone(source.updated_at)

    def test_create_git_source(self):
        source = ConfigSource.objects.create(source_type="git")
        self.assertEqual(source.source_type, "git")

    def test_create_manual_source(self):
        source = ConfigSource.objects.create(source_type="manual")
        self.assertEqual(source.source_type, "manual")

    def test_str_representation(self):
        source = ConfigSource.objects.create(source_type="api")
        self.assertEqual(str(source), f"ConfigSource {source.pk} (api)")

    def test_source_type_choices(self):
        field = ConfigSource._meta.get_field("source_type")
        choice_values = [c[0] for c in field.choices]
        self.assertIn("api", choice_values)
        self.assertIn("git", choice_values)
        self.assertIn("manual", choice_values)
```

**Step 2: Run tests to verify they fail**

```bash
cd /Users/aaronroth/Documents/netaudit/backend
python -m pytest config_sources/tests.py -v
```

Expected: ImportError or similar because ConfigSource model doesn't exist yet.

**Step 3: Write the ConfigSource model**

Write `backend/config_sources/models.py`:

```python
from django.db import models


class ConfigSource(models.Model):
    """
    Base model for device configuration sources.

    Uses Django multi-table inheritance. Each source type (API, Git, Manual)
    extends this with type-specific fields. The ``source_type`` discriminator
    tells callers which child table to query.
    """

    class SourceType(models.TextChoices):
        API = "api", "API Endpoint"
        GIT = "git", "Git Repository"
        MANUAL = "manual", "Manual"

    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ConfigSource {self.pk} ({self.source_type})"
```

**Step 4: Create and run migration**

```bash
cd /Users/aaronroth/Documents/netaudit/backend
python manage.py makemigrations config_sources
python -m pytest config_sources/tests.py -v
```

Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add backend/config_sources/
git commit -m "feat: add ConfigSource base model with source_type discriminator"
```

---

### Task 3: Add ApiConfigSource Child Model + Tests

**Files:**
- Modify: `backend/config_sources/models.py`
- Modify: `backend/config_sources/tests.py`

**Step 1: Write the failing tests**

Append to `backend/config_sources/tests.py`:

```python
from .models import ApiConfigSource


class ApiConfigSourceTests(TestCase):
    """Tests for the ApiConfigSource model."""

    def test_create_api_source(self):
        source = ApiConfigSource.objects.create(
            source_type="api",
            api_endpoint="https://router-1.lab.local/api/config",
            headers={"Authorization": "Bearer token123"},
        )
        self.assertEqual(source.source_type, "api")
        self.assertEqual(source.api_endpoint, "https://router-1.lab.local/api/config")
        self.assertEqual(source.headers, {"Authorization": "Bearer token123"})

    def test_api_source_inherits_config_source(self):
        source = ApiConfigSource.objects.create(
            source_type="api",
            api_endpoint="https://router-1.lab.local/api/config",
        )
        # Should also appear in ConfigSource table
        self.assertTrue(ConfigSource.objects.filter(pk=source.pk).exists())

    def test_api_source_endpoint_optional(self):
        source = ApiConfigSource.objects.create(
            source_type="api",
        )
        self.assertEqual(source.api_endpoint, "")

    def test_api_source_headers_default_empty(self):
        source = ApiConfigSource.objects.create(
            source_type="api",
        )
        self.assertEqual(source.headers, {})

    def test_api_source_effective_endpoint_uses_own(self):
        source = ApiConfigSource.objects.create(
            source_type="api",
            api_endpoint="https://custom.local/api",
        )
        self.assertEqual(source.effective_api_endpoint, "https://custom.local/api")

    def test_api_source_effective_endpoint_falls_back_to_default(self):
        from devices.models import Device
        from settings.models import SiteSettings

        site = SiteSettings.load()
        site.default_api_endpoint = "https://default.example.com/api"
        site.save()

        source = ApiConfigSource.objects.create(source_type="api")
        device = Device.objects.create(
            name="switch-99",
            hostname="switch-99.local",
            config_source=source.configsource_ptr,
        )
        self.assertEqual(
            source.effective_api_endpoint,
            "https://default.example.com/api/switch-99",
        )

    def test_api_source_effective_endpoint_empty_when_no_config(self):
        source = ApiConfigSource.objects.create(source_type="api")
        self.assertEqual(source.effective_api_endpoint, "")

    def test_str_representation(self):
        source = ApiConfigSource.objects.create(
            source_type="api",
            api_endpoint="https://router.local/api",
        )
        self.assertIn("api", str(source))
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest config_sources/tests.py::ApiConfigSourceTests -v
```

Expected: ImportError — `ApiConfigSource` not defined.

**Step 3: Write the ApiConfigSource model**

Append to `backend/config_sources/models.py`:

```python
class ApiConfigSource(ConfigSource):
    """
    Configuration source that fetches config via HTTP GET from an API endpoint.

    Mirrors the legacy Device.api_endpoint + DeviceHeader behavior.
    """

    api_endpoint = models.URLField(blank=True, default="")
    headers = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "API config source"

    def __str__(self):
        return f"ApiConfigSource {self.pk} ({self.api_endpoint or 'default'})"

    @property
    def effective_api_endpoint(self):
        """Return the endpoint URL, falling back to site-wide default."""
        if self.api_endpoint:
            return self.api_endpoint
        # Fall back to site-wide default + device name
        from settings.models import SiteSettings

        try:
            device = self.configsource_ptr.device
        except Exception:
            return ""
        site = SiteSettings.load()
        if site.default_api_endpoint:
            base = site.default_api_endpoint.rstrip("/")
            return f"{base}/{device.name}"
        return ""
```

Note: The `device` reverse relation will be available once we add the OneToOneField on Device in Task 6. The `test_api_source_effective_endpoint_falls_back_to_default` test depends on that field existing, so it should be skipped until Task 6. Add `@unittest.skip("Requires Device.config_source field — Task 6")` on that test for now.

**Step 4: Create migration and run tests**

```bash
cd /Users/aaronroth/Documents/netaudit/backend
python manage.py makemigrations config_sources
python -m pytest config_sources/tests.py -v
```

Expected: All non-skipped tests PASS.

**Step 5: Commit**

```bash
git add backend/config_sources/
git commit -m "feat: add ApiConfigSource model with endpoint and headers"
```

---

### Task 4: Add GitConfigSource Child Model + Tests

**Files:**
- Modify: `backend/config_sources/models.py`
- Modify: `backend/config_sources/tests.py`

**Step 1: Write the failing tests**

Append to `backend/config_sources/tests.py`:

```python
from .models import GitConfigSource


class GitConfigSourceTests(TestCase):
    """Tests for the GitConfigSource model."""

    def test_create_git_source(self):
        source = GitConfigSource.objects.create(
            source_type="git",
            repo_url="https://github.com/org/configs.git",
            branch="main",
            file_path="routers/router-1.cfg",
        )
        self.assertEqual(source.source_type, "git")
        self.assertEqual(source.repo_url, "https://github.com/org/configs.git")
        self.assertEqual(source.branch, "main")
        self.assertEqual(source.file_path, "routers/router-1.cfg")

    def test_git_source_inherits_config_source(self):
        source = GitConfigSource.objects.create(
            source_type="git",
            repo_url="https://github.com/org/configs.git",
            file_path="router.cfg",
        )
        self.assertTrue(ConfigSource.objects.filter(pk=source.pk).exists())

    def test_git_source_branch_defaults_to_main(self):
        source = GitConfigSource.objects.create(
            source_type="git",
            repo_url="https://github.com/org/configs.git",
            file_path="router.cfg",
        )
        self.assertEqual(source.branch, "main")

    def test_str_representation(self):
        source = GitConfigSource.objects.create(
            source_type="git",
            repo_url="https://github.com/org/configs.git",
            branch="main",
            file_path="routers/router-1.cfg",
        )
        self.assertIn("git", str(source))
```

**Step 2: Run to verify failure, then implement**

Append to `backend/config_sources/models.py`:

```python
class GitConfigSource(ConfigSource):
    """
    Configuration source that reads config from a file in a git repository.

    The repo is cloned/pulled to a persistent cache directory. The config
    text is read from ``file_path`` relative to the repo root on the
    specified ``branch``.
    """

    repo_url = models.URLField()
    branch = models.CharField(max_length=255, default="main")
    file_path = models.CharField(max_length=1024)

    class Meta:
        verbose_name = "Git config source"

    def __str__(self):
        return f"GitConfigSource {self.pk} ({self.repo_url} @ {self.branch}:{self.file_path})"
```

**Step 3: Create migration and run tests**

```bash
python manage.py makemigrations config_sources
python -m pytest config_sources/tests.py -v
```

Expected: All tests PASS.

**Step 4: Commit**

```bash
git add backend/config_sources/
git commit -m "feat: add GitConfigSource model with repo_url, branch, file_path"
```

---

### Task 5: Add ManualConfigSource Child Model + Tests

**Files:**
- Modify: `backend/config_sources/models.py`
- Modify: `backend/config_sources/tests.py`

**Step 1: Write the failing tests**

Append to `backend/config_sources/tests.py`:

```python
from .models import ManualConfigSource


class ManualConfigSourceTests(TestCase):
    """Tests for the ManualConfigSource model."""

    def test_create_manual_source(self):
        config_text = "hostname router-1\ninterface GigabitEthernet0/0\n ip address 10.0.0.1 255.255.255.0"
        source = ManualConfigSource.objects.create(
            source_type="manual",
            config_text=config_text,
        )
        self.assertEqual(source.source_type, "manual")
        self.assertEqual(source.config_text, config_text)

    def test_manual_source_inherits_config_source(self):
        source = ManualConfigSource.objects.create(
            source_type="manual",
            config_text="hostname test",
        )
        self.assertTrue(ConfigSource.objects.filter(pk=source.pk).exists())

    def test_str_representation(self):
        source = ManualConfigSource.objects.create(
            source_type="manual",
            config_text="hostname test",
        )
        self.assertIn("manual", str(source).lower())
```

**Step 2: Run to verify failure, then implement**

Append to `backend/config_sources/models.py`:

```python
class ManualConfigSource(ConfigSource):
    """
    Configuration source where the user directly provides config text.
    """

    config_text = models.TextField()

    class Meta:
        verbose_name = "Manual config source"

    def __str__(self):
        preview = self.config_text[:50] + "..." if len(self.config_text) > 50 else self.config_text
        return f"ManualConfigSource {self.pk} ({preview})"
```

**Step 3: Create migration and run tests**

```bash
python manage.py makemigrations config_sources
python -m pytest config_sources/tests.py -v
```

Expected: All tests PASS.

**Step 4: Commit**

```bash
git add backend/config_sources/
git commit -m "feat: add ManualConfigSource model with config_text field"
```

---

### Task 6: Add config_source FK + Cached Config Fields to Device

**Files:**
- Modify: `backend/devices/models.py`
- Modify: `backend/config_sources/tests.py` (unskip the fallback test)

**Step 1: Write the failing test**

Add to `backend/config_sources/tests.py`:

```python
class DeviceConfigSourceLinkTests(TestCase):
    """Tests for Device ↔ ConfigSource relationship."""

    def test_device_with_api_source(self):
        from devices.models import Device

        source = ApiConfigSource.objects.create(
            source_type="api",
            api_endpoint="https://router.local/api",
        )
        device = Device.objects.create(
            name="linked-device",
            hostname="linked.local",
            config_source=source.configsource_ptr,
        )
        self.assertEqual(device.config_source.source_type, "api")
        self.assertEqual(device.config_source.apiconfigsource.api_endpoint, "https://router.local/api")

    def test_device_without_config_source(self):
        from devices.models import Device

        device = Device.objects.create(
            name="no-source",
            hostname="no-source.local",
        )
        self.assertIsNone(device.config_source)

    def test_device_last_fetched_config_default_empty(self):
        from devices.models import Device

        device = Device.objects.create(
            name="empty-cache",
            hostname="empty.local",
        )
        self.assertEqual(device.last_fetched_config, "")
        self.assertIsNone(device.config_fetched_at)

    def test_delete_config_source_sets_null_on_device(self):
        from devices.models import Device

        source = ManualConfigSource.objects.create(
            source_type="manual",
            config_text="test",
        )
        device = Device.objects.create(
            name="will-lose-source",
            hostname="lose.local",
            config_source=source.configsource_ptr,
        )
        source.delete()
        device.refresh_from_db()
        self.assertIsNone(device.config_source)
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest config_sources/tests.py::DeviceConfigSourceLinkTests -v
```

Expected: TypeError or similar — Device model doesn't have `config_source` field yet.

**Step 3: Add fields to Device model**

Modify `backend/devices/models.py`. Add the import at the top and the new fields to the Device model:

After `from django.db import models`, add nothing extra (we'll use a string reference to avoid circular import).

Add these fields to the `Device` model class (after `groups` field, before `created_at`):

```python
    config_source = models.OneToOneField(
        "config_sources.ConfigSource",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="device",
    )
    last_fetched_config = models.TextField(blank=True, default="")
    config_fetched_at = models.DateTimeField(null=True, blank=True)
```

**Step 4: Create migration and run tests**

```bash
python manage.py makemigrations devices
python -m pytest config_sources/tests.py -v
```

Now also unskip the `test_api_source_effective_endpoint_falls_back_to_default` test and re-run.

Expected: All tests PASS.

**Step 5: Commit**

```bash
git add backend/devices/ backend/config_sources/
git commit -m "feat: add config_source FK and cached config fields to Device"
```

---

### Task 7: Write Fetcher Layer + Tests

**Files:**
- Create: `backend/config_sources/fetchers.py`
- Create: `backend/config_sources/test_fetchers.py`

**Step 1: Write the failing tests**

Create `backend/config_sources/test_fetchers.py`:

```python
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase, override_settings

from devices.models import Device

from .fetchers import fetch_config, _fetch_api, _fetch_git, _fetch_manual
from .models import ApiConfigSource, GitConfigSource, ManualConfigSource


class FetchConfigDispatchTests(TestCase):
    """Tests for the top-level fetch_config dispatcher."""

    def test_raises_when_no_config_source(self):
        device = Device.objects.create(name="no-source", hostname="x.local")
        with self.assertRaises(ValueError) as ctx:
            fetch_config(device)
        self.assertIn("no config source", str(ctx.exception))

    @patch("config_sources.fetchers._fetch_api")
    def test_dispatches_to_api_fetcher(self, mock_fetch):
        mock_fetch.return_value = "api config text"
        source = ApiConfigSource.objects.create(
            source_type="api",
            api_endpoint="https://r.local/api",
        )
        device = Device.objects.create(
            name="api-dev", hostname="x.local",
            config_source=source.configsource_ptr,
        )
        result = fetch_config(device)
        self.assertEqual(result, "api config text")
        mock_fetch.assert_called_once()
        device.refresh_from_db()
        self.assertEqual(device.last_fetched_config, "api config text")
        self.assertIsNotNone(device.config_fetched_at)

    @patch("config_sources.fetchers._fetch_git")
    def test_dispatches_to_git_fetcher(self, mock_fetch):
        mock_fetch.return_value = "git config text"
        source = GitConfigSource.objects.create(
            source_type="git",
            repo_url="https://github.com/org/configs.git",
            file_path="r.cfg",
        )
        device = Device.objects.create(
            name="git-dev", hostname="x.local",
            config_source=source.configsource_ptr,
        )
        result = fetch_config(device)
        self.assertEqual(result, "git config text")
        mock_fetch.assert_called_once()

    def test_dispatches_to_manual_fetcher(self):
        source = ManualConfigSource.objects.create(
            source_type="manual",
            config_text="manual config text",
        )
        device = Device.objects.create(
            name="manual-dev", hostname="x.local",
            config_source=source.configsource_ptr,
        )
        result = fetch_config(device)
        self.assertEqual(result, "manual config text")


class FetchApiTests(TestCase):
    """Tests for the _fetch_api fetcher."""

    @patch("config_sources.fetchers.requests.get")
    def test_fetches_from_endpoint(self, mock_get):
        mock_response = Mock()
        mock_response.text = "hostname router-1"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        source = ApiConfigSource.objects.create(
            source_type="api",
            api_endpoint="https://router.local/api/config",
            headers={"Authorization": "Bearer abc"},
        )
        result = _fetch_api(source)
        self.assertEqual(result, "hostname router-1")
        mock_get.assert_called_once_with(
            "https://router.local/api/config",
            headers={"Authorization": "Bearer abc"},
            timeout=30,
        )

    @patch("config_sources.fetchers.requests.get")
    def test_raises_on_http_error(self, mock_get):
        import requests as req
        mock_get.side_effect = req.RequestException("Connection refused")

        source = ApiConfigSource.objects.create(
            source_type="api",
            api_endpoint="https://bad.local/api",
        )
        with self.assertRaises(req.RequestException):
            _fetch_api(source)

    def test_raises_when_no_endpoint(self):
        source = ApiConfigSource.objects.create(source_type="api")
        with self.assertRaises(ValueError):
            _fetch_api(source)


class FetchManualTests(TestCase):
    """Tests for the _fetch_manual fetcher."""

    def test_returns_config_text(self):
        source = ManualConfigSource.objects.create(
            source_type="manual",
            config_text="hostname switch-1\nvlan 10",
        )
        result = _fetch_manual(source)
        self.assertEqual(result, "hostname switch-1\nvlan 10")


class FetchGitTests(TestCase):
    """Tests for the _fetch_git fetcher."""

    @patch("config_sources.fetchers.subprocess.run")
    def test_clones_and_reads_file(self, mock_run):
        import tempfile
        cache_dir = Path(tempfile.mkdtemp())

        source = GitConfigSource.objects.create(
            source_type="git",
            repo_url="https://github.com/org/configs.git",
            branch="main",
            file_path="routers/r1.cfg",
        )

        # Mock subprocess calls (clone, checkout)
        mock_run.return_value = Mock(returncode=0)

        # Create the expected file structure in the cache dir
        repo_dir = cache_dir / "configs"
        repo_dir.mkdir(parents=True)
        (repo_dir / "routers").mkdir()
        (repo_dir / "routers" / "r1.cfg").write_text("hostname router-1")

        with patch("config_sources.fetchers._get_git_cache_dir", return_value=cache_dir):
            with patch("config_sources.fetchers._repo_exists", return_value=False):
                result = _fetch_git(source)

        self.assertEqual(result, "hostname router-1")

    def test_raises_when_file_not_found(self):
        import tempfile
        cache_dir = Path(tempfile.mkdtemp())

        source = GitConfigSource.objects.create(
            source_type="git",
            repo_url="https://github.com/org/configs.git",
            branch="main",
            file_path="nonexistent.cfg",
        )

        repo_dir = cache_dir / "configs"
        repo_dir.mkdir(parents=True)

        with patch("config_sources.fetchers._get_git_cache_dir", return_value=cache_dir):
            with patch("config_sources.fetchers._repo_exists", return_value=True):
                with patch("config_sources.fetchers.subprocess.run", return_value=Mock(returncode=0)):
                    with self.assertRaises(FileNotFoundError):
                        _fetch_git(source)
```

**Step 2: Run tests to verify they fail**

```bash
python -m pytest config_sources/test_fetchers.py -v
```

Expected: ImportError — `fetchers` module doesn't exist.

**Step 3: Write the fetchers module**

Create `backend/config_sources/fetchers.py`:

```python
"""
Config source fetcher dispatch layer.

Each source type has a dedicated fetcher function. The top-level
``fetch_config`` dispatches based on the source's ``source_type``
discriminator and persists the result on the device.
"""

import hashlib
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests
from django.conf import settings

from .models import ApiConfigSource, GitConfigSource, ManualConfigSource

logger = logging.getLogger(__name__)


def fetch_config(device) -> str:
    """
    Fetch config text from the device's configured source.

    Dispatches to the appropriate fetcher based on ``source_type``,
    then persists the result to ``device.last_fetched_config``.

    Parameters
    ----------
    device : devices.models.Device
        The device whose config to fetch.

    Returns
    -------
    str
        The raw configuration text.

    Raises
    ------
    ValueError
        If the device has no config source configured.
    """
    source = device.config_source
    if source is None:
        raise ValueError(
            f"Device '{device.name}' has no config source configured"
        )

    match source.source_type:
        case "api":
            text = _fetch_api(source.apiconfigsource)
        case "git":
            text = _fetch_git(source.gitconfigsource)
        case "manual":
            text = _fetch_manual(source.manualconfigsource)
        case _:
            raise ValueError(f"Unknown source type: {source.source_type}")

    device.last_fetched_config = text
    device.config_fetched_at = datetime.now(timezone.utc)
    device.save(update_fields=["last_fetched_config", "config_fetched_at"])
    return text


def _fetch_api(source: ApiConfigSource) -> str:
    """Fetch config via HTTP GET from the API endpoint."""
    endpoint = source.effective_api_endpoint
    if not endpoint:
        raise ValueError(
            "API config source has no endpoint configured "
            "and no default endpoint is set."
        )
    headers = source.headers or {}
    response = requests.get(endpoint, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def _fetch_manual(source: ManualConfigSource) -> str:
    """Return the manually-entered config text."""
    return source.config_text


def _fetch_git(source: GitConfigSource) -> str:
    """
    Clone or pull a git repo and read the config file.

    Uses a persistent cache directory. First fetch clones; subsequent
    fetches do ``git fetch`` + ``git checkout``.
    """
    cache_dir = _get_git_cache_dir()
    repo_name = _repo_dir_name(source.repo_url)
    repo_dir = cache_dir / repo_name

    if _repo_exists(repo_dir):
        # Pull latest changes
        subprocess.run(
            ["git", "fetch", "--all"],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            timeout=120,
        )
    else:
        # Clone the repository
        subprocess.run(
            ["git", "clone", source.repo_url, str(repo_dir)],
            check=True,
            capture_output=True,
            timeout=300,
        )

    # Checkout the specified branch
    subprocess.run(
        ["git", "checkout", f"origin/{source.branch}"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        timeout=30,
    )

    # Read the file
    config_file = repo_dir / source.file_path
    if not config_file.exists():
        raise FileNotFoundError(
            f"Config file '{source.file_path}' not found in repo "
            f"'{source.repo_url}' on branch '{source.branch}'"
        )
    return config_file.read_text()


def _get_git_cache_dir() -> Path:
    """Return the git cache directory, creating it if needed."""
    cache_dir = Path(
        getattr(settings, "GIT_CACHE_DIR", "/tmp/netaudit-git-cache")
    )
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _repo_exists(repo_dir: Path) -> bool:
    """Check if a repo directory exists and is a git repo."""
    return (repo_dir / ".git").is_dir()


def _repo_dir_name(repo_url: str) -> str:
    """
    Derive a stable directory name from a repo URL.

    Strips protocol and ``.git`` suffix, replaces slashes and special
    chars. Appends a short hash for uniqueness.
    """
    # Strip protocol
    name = repo_url.split("://", 1)[-1] if "://" in repo_url else repo_url
    # Strip .git suffix
    if name.endswith(".git"):
        name = name[:-4]
    # Replace path separators and special chars
    name = name.replace("/", "_").replace(":", "_")
    # Append short hash for collision resistance
    url_hash = hashlib.sha256(repo_url.encode()).hexdigest()[:8]
    return f"{name}_{url_hash}"
```

**Step 4: Add GIT_CACHE_DIR to settings**

In `backend/config/settings/base.py`, add after line 130 (`AUDIT_RUNNER_TIMEOUT`):

```python
# Git config source cache directory
GIT_CACHE_DIR = os.environ.get("GIT_CACHE_DIR", "/tmp/netaudit-git-cache")
```

**Step 5: Run tests**

```bash
python -m pytest config_sources/test_fetchers.py -v
```

Expected: All tests PASS.

**Step 6: Commit**

```bash
git add backend/config_sources/fetchers.py backend/config_sources/test_fetchers.py backend/config/settings/base.py
git commit -m "feat: add config source fetcher dispatch layer (api, git, manual)"
```

---

### Task 8: Write ConfigSource Serializers + Tests

**Files:**
- Create: `backend/config_sources/serializers.py`
- Create: `backend/config_sources/test_serializers.py`

**Step 1: Write the failing tests**

Create `backend/config_sources/test_serializers.py`:

```python
from django.test import TestCase

from .serializers import ConfigSourceSerializer
from .models import ApiConfigSource, GitConfigSource, ManualConfigSource


class ConfigSourceSerializerTests(TestCase):
    """Tests for the discriminated ConfigSourceSerializer."""

    def test_serialize_api_source(self):
        source = ApiConfigSource.objects.create(
            source_type="api",
            api_endpoint="https://router.local/api",
            headers={"Authorization": "Bearer abc"},
        )
        data = ConfigSourceSerializer(source.configsource_ptr).data
        self.assertEqual(data["source_type"], "api")
        self.assertEqual(data["api_endpoint"], "https://router.local/api")
        self.assertEqual(data["headers"], {"Authorization": "Bearer abc"})

    def test_serialize_git_source(self):
        source = GitConfigSource.objects.create(
            source_type="git",
            repo_url="https://github.com/org/configs.git",
            branch="main",
            file_path="router.cfg",
        )
        data = ConfigSourceSerializer(source.configsource_ptr).data
        self.assertEqual(data["source_type"], "git")
        self.assertEqual(data["repo_url"], "https://github.com/org/configs.git")
        self.assertEqual(data["branch"], "main")
        self.assertEqual(data["file_path"], "router.cfg")

    def test_serialize_manual_source(self):
        source = ManualConfigSource.objects.create(
            source_type="manual",
            config_text="hostname test",
        )
        data = ConfigSourceSerializer(source.configsource_ptr).data
        self.assertEqual(data["source_type"], "manual")
        self.assertEqual(data["config_text"], "hostname test")

    def test_deserialize_api_source(self):
        data = {
            "source_type": "api",
            "api_endpoint": "https://router.local/api",
            "headers": {"Auth": "Bearer x"},
        }
        serializer = ConfigSourceSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        source = serializer.save()
        self.assertIsInstance(source, ApiConfigSource)
        self.assertEqual(source.api_endpoint, "https://router.local/api")

    def test_deserialize_git_source(self):
        data = {
            "source_type": "git",
            "repo_url": "https://github.com/org/configs.git",
            "branch": "develop",
            "file_path": "switches/sw1.cfg",
        }
        serializer = ConfigSourceSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        source = serializer.save()
        self.assertIsInstance(source, GitConfigSource)
        self.assertEqual(source.branch, "develop")

    def test_deserialize_manual_source(self):
        data = {
            "source_type": "manual",
            "config_text": "hostname switch-1",
        }
        serializer = ConfigSourceSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        source = serializer.save()
        self.assertIsInstance(source, ManualConfigSource)

    def test_deserialize_missing_source_type(self):
        serializer = ConfigSourceSerializer(data={"api_endpoint": "https://x.local"})
        self.assertFalse(serializer.is_valid())
        self.assertIn("source_type", serializer.errors)

    def test_deserialize_invalid_source_type(self):
        serializer = ConfigSourceSerializer(data={"source_type": "invalid"})
        self.assertFalse(serializer.is_valid())

    def test_deserialize_git_missing_required_fields(self):
        data = {"source_type": "git"}
        serializer = ConfigSourceSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_deserialize_manual_missing_config_text(self):
        data = {"source_type": "manual"}
        serializer = ConfigSourceSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_update_api_source(self):
        source = ApiConfigSource.objects.create(
            source_type="api",
            api_endpoint="https://old.local/api",
        )
        serializer = ConfigSourceSerializer(
            source.configsource_ptr,
            data={
                "source_type": "api",
                "api_endpoint": "https://new.local/api",
                "headers": {"X-New": "val"},
            },
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated = serializer.save()
        self.assertEqual(updated.api_endpoint, "https://new.local/api")
```

**Step 2: Run to verify failure, then implement**

Create `backend/config_sources/serializers.py`:

```python
from rest_framework import serializers

from .models import (
    ApiConfigSource,
    ConfigSource,
    GitConfigSource,
    ManualConfigSource,
)


class ConfigSourceSerializer(serializers.Serializer):
    """
    Discriminated serializer for config sources.

    Validates and creates/updates the appropriate child model based
    on ``source_type``.
    """

    source_type = serializers.ChoiceField(choices=ConfigSource.SourceType.choices)

    # API fields
    api_endpoint = serializers.URLField(required=False, default="", allow_blank=True)
    headers = serializers.JSONField(required=False, default=dict)
    effective_api_endpoint = serializers.CharField(read_only=True, required=False)

    # Git fields
    repo_url = serializers.URLField(required=False)
    branch = serializers.CharField(required=False, default="main")
    file_path = serializers.CharField(required=False)

    # Manual fields
    config_text = serializers.CharField(required=False)

    def validate(self, data):
        source_type = data.get("source_type")

        if source_type == "git":
            if not data.get("repo_url"):
                raise serializers.ValidationError(
                    {"repo_url": "This field is required for git sources."}
                )
            if not data.get("file_path"):
                raise serializers.ValidationError(
                    {"file_path": "This field is required for git sources."}
                )

        if source_type == "manual":
            if not data.get("config_text"):
                raise serializers.ValidationError(
                    {"config_text": "This field is required for manual sources."}
                )

        return data

    def to_representation(self, instance):
        """Serialize the child model fields based on source_type."""
        data = {
            "source_type": instance.source_type,
        }

        if instance.source_type == "api":
            child = instance.apiconfigsource
            data["api_endpoint"] = child.api_endpoint
            data["headers"] = child.headers
            data["effective_api_endpoint"] = child.effective_api_endpoint
        elif instance.source_type == "git":
            child = instance.gitconfigsource
            data["repo_url"] = child.repo_url
            data["branch"] = child.branch
            data["file_path"] = child.file_path
        elif instance.source_type == "manual":
            child = instance.manualconfigsource
            data["config_text"] = child.config_text

        return data

    def create(self, validated_data):
        source_type = validated_data["source_type"]

        if source_type == "api":
            return ApiConfigSource.objects.create(
                source_type="api",
                api_endpoint=validated_data.get("api_endpoint", ""),
                headers=validated_data.get("headers", {}),
            )
        elif source_type == "git":
            return GitConfigSource.objects.create(
                source_type="git",
                repo_url=validated_data["repo_url"],
                branch=validated_data.get("branch", "main"),
                file_path=validated_data["file_path"],
            )
        elif source_type == "manual":
            return ManualConfigSource.objects.create(
                source_type="manual",
                config_text=validated_data["config_text"],
            )

    def update(self, instance, validated_data):
        source_type = validated_data["source_type"]

        if source_type != instance.source_type:
            # Source type changed — delete old child, create new one
            instance.delete()
            return self.create(validated_data)

        # Update in-place on the child
        if source_type == "api":
            child = instance.apiconfigsource
            child.api_endpoint = validated_data.get("api_endpoint", child.api_endpoint)
            child.headers = validated_data.get("headers", child.headers)
            child.save()
            return child
        elif source_type == "git":
            child = instance.gitconfigsource
            child.repo_url = validated_data.get("repo_url", child.repo_url)
            child.branch = validated_data.get("branch", child.branch)
            child.file_path = validated_data.get("file_path", child.file_path)
            child.save()
            return child
        elif source_type == "manual":
            child = instance.manualconfigsource
            child.config_text = validated_data.get("config_text", child.config_text)
            child.save()
            return child
```

**Step 3: Run tests**

```bash
python -m pytest config_sources/test_serializers.py -v
```

Expected: All tests PASS.

**Step 4: Commit**

```bash
git add backend/config_sources/serializers.py backend/config_sources/test_serializers.py
git commit -m "feat: add discriminated ConfigSourceSerializer"
```

---

### Task 9: Update Device Serializer for Inline Config Source

**Files:**
- Modify: `backend/devices/serializers.py`
- Modify: `backend/devices/tests.py`

**Step 1: Write the failing tests**

Add new test class to `backend/devices/tests.py`:

```python
class DeviceAPIConfigSourceTests(APITestCase):
    """Tests for Device API with config_source inline."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com",
            password="testpass123", role="admin",
        )
        self.client.force_authenticate(user=self.user)
        self.list_url = reverse("device-list")

    def test_create_device_with_api_source(self):
        data = {
            "name": "api-sourced",
            "hostname": "api.local",
            "enabled": True,
            "config_source": {
                "source_type": "api",
                "api_endpoint": "https://api.local/config",
                "headers": {"Authorization": "Bearer token"},
            },
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["config_source"]["source_type"], "api")
        self.assertEqual(response.data["config_source"]["api_endpoint"], "https://api.local/config")

    def test_create_device_with_git_source(self):
        data = {
            "name": "git-sourced",
            "hostname": "git.local",
            "enabled": True,
            "config_source": {
                "source_type": "git",
                "repo_url": "https://github.com/org/configs.git",
                "branch": "main",
                "file_path": "routers/r1.cfg",
            },
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["config_source"]["source_type"], "git")

    def test_create_device_with_manual_source(self):
        data = {
            "name": "manual-sourced",
            "hostname": "manual.local",
            "enabled": True,
            "config_source": {
                "source_type": "manual",
                "config_text": "hostname router-1",
            },
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["config_source"]["source_type"], "manual")

    def test_create_device_without_config_source(self):
        data = {
            "name": "no-source",
            "hostname": "none.local",
            "enabled": True,
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["config_source"])

    def test_update_device_config_source(self):
        # Create with API source
        data = {
            "name": "will-change",
            "hostname": "change.local",
            "enabled": True,
            "config_source": {
                "source_type": "api",
                "api_endpoint": "https://old.local/api",
            },
        }
        response = self.client.post(self.list_url, data, format="json")
        device_id = response.data["id"]

        # Update to git source
        update_data = {
            "config_source": {
                "source_type": "git",
                "repo_url": "https://github.com/org/configs.git",
                "file_path": "r1.cfg",
            },
        }
        detail_url = reverse("device-detail", kwargs={"pk": device_id})
        response = self.client.patch(detail_url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["config_source"]["source_type"], "git")

    def test_response_includes_cached_config_fields(self):
        data = {
            "name": "with-cache",
            "hostname": "cache.local",
            "enabled": True,
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertIn("last_fetched_config", response.data)
        self.assertIn("config_fetched_at", response.data)
```

**Step 2: Run to verify failure**

```bash
python -m pytest devices/tests.py::DeviceAPIConfigSourceTests -v
```

Expected: Failures because serializer doesn't handle `config_source`.

**Step 3: Update the Device serializer**

Replace `backend/devices/serializers.py` with:

```python
from rest_framework import serializers

from config_sources.serializers import ConfigSourceSerializer
from .models import Device, DeviceGroup


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
    config_source = ConfigSourceSerializer(required=False, allow_null=True)
    groups = serializers.PrimaryKeyRelatedField(
        many=True, queryset=DeviceGroup.objects.all(), required=False,
    )

    class Meta:
        model = Device
        fields = [
            "id",
            "name",
            "hostname",
            "enabled",
            "config_source",
            "last_fetched_config",
            "config_fetched_at",
            "groups",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["last_fetched_config", "config_fetched_at"]

    def create(self, validated_data):
        config_source_data = validated_data.pop("config_source", None)
        groups_data = validated_data.pop("groups", [])

        # Create config source if provided
        config_source = None
        if config_source_data:
            cs_serializer = ConfigSourceSerializer(data=config_source_data)
            cs_serializer.is_valid(raise_exception=True)
            config_source = cs_serializer.save()

        device = Device.objects.create(
            config_source=config_source.configsource_ptr if config_source else None,
            **validated_data,
        )
        if groups_data:
            device.groups.set(groups_data)
        return device

    def update(self, instance, validated_data):
        config_source_data = validated_data.pop("config_source", None)
        groups_data = validated_data.pop("groups", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Handle config source update
        if config_source_data is not None:
            if instance.config_source:
                # Update existing
                cs_serializer = ConfigSourceSerializer(
                    instance.config_source, data=config_source_data,
                )
                cs_serializer.is_valid(raise_exception=True)
                new_source = cs_serializer.save()
                # If type changed, the old was deleted and new was created
                instance.config_source = getattr(
                    new_source, "configsource_ptr", new_source
                )
            else:
                # Create new
                cs_serializer = ConfigSourceSerializer(data=config_source_data)
                cs_serializer.is_valid(raise_exception=True)
                new_source = cs_serializer.save()
                instance.config_source = getattr(
                    new_source, "configsource_ptr", new_source
                )

        instance.save()

        if groups_data is not None:
            instance.groups.set(groups_data)

        return instance
```

**Step 4: Run tests**

```bash
python -m pytest devices/tests.py::DeviceAPIConfigSourceTests -v
```

Expected: All tests PASS.

**Step 5: Commit**

```bash
git add backend/devices/serializers.py backend/devices/tests.py
git commit -m "feat: update Device serializer with inline config_source support"
```

---

### Task 10: Update Device Views (fetch_config + test_connection)

**Files:**
- Modify: `backend/devices/views.py`
- Modify: `backend/devices/tests.py`

**Step 1: Write the failing tests**

Add to `backend/devices/tests.py`:

```python
from unittest.mock import patch, Mock


class DeviceFetchConfigAPITests(APITestCase):
    """Tests for the updated fetch_config action."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        from config_sources.models import ApiConfigSource, ManualConfigSource

        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com",
            password="testpass123", role="admin",
        )
        self.client.force_authenticate(user=self.user)

    @patch("config_sources.fetchers._fetch_api")
    def test_fetch_config_api_source(self, mock_fetch):
        from config_sources.models import ApiConfigSource
        mock_fetch.return_value = "hostname router-1"

        source = ApiConfigSource.objects.create(
            source_type="api",
            api_endpoint="https://r.local/api",
        )
        device = Device.objects.create(
            name="fetch-api", hostname="x.local",
            config_source=source.configsource_ptr,
        )

        url = reverse("device-fetch-config", kwargs={"pk": device.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["config"], "hostname router-1")

    def test_fetch_config_manual_source(self):
        from config_sources.models import ManualConfigSource
        source = ManualConfigSource.objects.create(
            source_type="manual",
            config_text="hostname switch-1",
        )
        device = Device.objects.create(
            name="fetch-manual", hostname="x.local",
            config_source=source.configsource_ptr,
        )
        url = reverse("device-fetch-config", kwargs={"pk": device.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["config"], "hostname switch-1")

    def test_fetch_config_no_source(self):
        device = Device.objects.create(name="no-src", hostname="x.local")
        url = reverse("device-fetch-config", kwargs={"pk": device.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)


class DeviceTestConnectionUpdatedTests(APITestCase):
    """Tests for test_connection with config source."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com",
            password="testpass123", role="admin",
        )
        self.client.force_authenticate(user=self.user)

    @patch("devices.views.requests.get")
    def test_test_connection_with_api_source(self, mock_get):
        from config_sources.models import ApiConfigSource
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"OK"
        mock_get.return_value = mock_response

        source = ApiConfigSource.objects.create(
            source_type="api",
            api_endpoint="https://r.local/api",
            headers={"Auth": "Bearer x"},
        )
        device = Device.objects.create(
            name="test-conn", hostname="x.local",
            config_source=source.configsource_ptr,
        )

        url = reverse("device-test-connection", kwargs={"pk": device.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])
        mock_get.assert_called_once_with(
            "https://r.local/api",
            headers={"Auth": "Bearer x"},
            timeout=10,
        )

    def test_test_connection_non_api_source_returns_error(self):
        from config_sources.models import ManualConfigSource
        source = ManualConfigSource.objects.create(
            source_type="manual", config_text="x",
        )
        device = Device.objects.create(
            name="manual-conn", hostname="x.local",
            config_source=source.configsource_ptr,
        )
        url = reverse("device-test-connection", kwargs={"pk": device.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
```

**Step 2: Run to verify failure, then update the views**

Rewrite `backend/devices/views.py`:

```python
import requests
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import IsEditorOrAbove, IsViewerOrAbove
from audits import tasks as audit_tasks
from config_sources.fetchers import fetch_config

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
    queryset = Device.objects.select_related("config_source").all()
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
        """Test HTTP connectivity — only works for API config sources."""
        device = self.get_object()
        source = device.config_source

        if source is None or source.source_type != "api":
            return Response(
                {
                    "success": False,
                    "error": "Test connection is only available for API config sources.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        api_source = source.apiconfigsource
        endpoint = api_source.effective_api_endpoint
        if not endpoint:
            return Response(
                {
                    "success": False,
                    "error": "No API endpoint configured and no default endpoint is set.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        headers = api_source.headers or {}
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

    @action(detail=True, methods=["post"], url_path="fetch-config", url_name="fetch-config")
    def fetch_config(self, request, pk=None):
        """Fetch config from the device's configured source."""
        device = self.get_object()
        if device.config_source is None:
            return Response(
                {"error": "No config source configured for this device."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            config_text = fetch_config(device)
            return Response({"config": config_text})
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
```

**Step 3: Run tests**

```bash
python -m pytest devices/tests.py::DeviceFetchConfigAPITests devices/tests.py::DeviceTestConnectionUpdatedTests -v
```

Expected: All tests PASS.

**Step 4: Commit**

```bash
git add backend/devices/views.py backend/devices/tests.py
git commit -m "feat: update device views to use config source fetchers"
```

---

### Task 11: Update Audit Service to Use Config Source Fetcher

**Files:**
- Modify: `backend/audits/services.py:62,167-184`
- Modify: `backend/audits/test_services.py`

**Step 1: Update services.py**

In `backend/audits/services.py`:

1. Replace the import `import requests` (line 16) — remove it (no longer needed in this module).
2. Add import: `from config_sources.fetchers import fetch_config as fetch_device_config`
3. Replace line 62 (`config_text = _fetch_config(device)`) with: `config_text = fetch_device_config(device)`
4. Delete the `_fetch_config` helper function (lines 167-184).

**Step 2: Update audit service tests**

In `backend/audits/test_services.py`, find tests that mock `audits.services._fetch_config` and update them to mock `config_sources.fetchers._fetch_api` (or use devices with ManualConfigSource for simplicity). The exact changes depend on the test patterns — the key is that `_fetch_config` is no longer in `audits.services`.

Specifically, update mocks from:
- `@patch("audits.services._fetch_config")` → create a ManualConfigSource on the test device and skip the mock (for simple cases), or mock `config_sources.fetchers.fetch_config`.

**Step 3: Run full test suite**

```bash
python -m pytest backend/ -v --timeout=60
```

Expected: All tests PASS.

**Step 4: Commit**

```bash
git add backend/audits/services.py backend/audits/test_services.py
git commit -m "refactor: use config_sources.fetchers in audit service"
```

---

### Task 12: Data Migration — Migrate Existing Devices

**Files:**
- Create: `backend/devices/migrations/XXXX_migrate_to_config_sources.py` (data migration)

**Step 1: Write the data migration**

```bash
cd /Users/aaronroth/Documents/netaudit/backend
python manage.py makemigrations devices --empty --name migrate_to_config_sources
```

Then edit the generated file:

```python
from django.db import migrations


def migrate_devices_to_config_sources(apps, schema_editor):
    """
    For each Device that has an api_endpoint or headers,
    create an ApiConfigSource and link it.
    """
    Device = apps.get_model("devices", "Device")
    DeviceHeader = apps.get_model("devices", "DeviceHeader")
    ConfigSource = apps.get_model("config_sources", "ConfigSource")
    ApiConfigSource = apps.get_model("config_sources", "ApiConfigSource")

    for device in Device.objects.all():
        headers_qs = DeviceHeader.objects.filter(device=device)
        has_endpoint = bool(device.api_endpoint)
        has_headers = headers_qs.exists()

        if has_endpoint or has_headers:
            # Create base ConfigSource
            cs = ConfigSource.objects.create(source_type="api")
            # Create ApiConfigSource child
            headers_dict = {h.key: h.value for h in headers_qs}
            ApiConfigSource.objects.create(
                configsource_ptr=cs,
                source_type="api",
                api_endpoint=device.api_endpoint,
                headers=headers_dict,
            )
            # Link to device
            device.config_source = cs
            device.save(update_fields=["config_source"])


def reverse_migration(apps, schema_editor):
    """Reverse: copy config source data back to device fields."""
    Device = apps.get_model("devices", "Device")
    DeviceHeader = apps.get_model("devices", "DeviceHeader")

    for device in Device.objects.filter(config_source__isnull=False):
        cs = device.config_source
        if cs.source_type == "api":
            try:
                api_source = cs.apiconfigsource
                device.api_endpoint = api_source.api_endpoint
                device.save(update_fields=["api_endpoint"])
                for key, value in (api_source.headers or {}).items():
                    DeviceHeader.objects.get_or_create(
                        device=device, key=key, defaults={"value": value},
                    )
            except Exception:
                pass


class Migration(migrations.Migration):
    dependencies = [
        ("devices", "XXXX_previous"),  # Replace with actual previous migration name
        ("config_sources", "XXXX_latest"),  # Replace with latest config_sources migration
    ]

    operations = [
        migrations.RunPython(
            migrate_devices_to_config_sources,
            reverse_migration,
        ),
    ]
```

Replace the dependency migration names with the actual ones.

**Step 2: Run migration**

```bash
python manage.py migrate
```

**Step 3: Verify migration worked**

```bash
python manage.py shell -c "
from devices.models import Device
for d in Device.objects.all():
    print(f'{d.name}: config_source={d.config_source}')
"
```

**Step 4: Commit**

```bash
git add backend/devices/migrations/
git commit -m "data: migrate existing device endpoints to ApiConfigSource"
```

---

### Task 13: Remove Legacy Fields (api_endpoint, DeviceHeader, effective_api_endpoint)

**Files:**
- Modify: `backend/devices/models.py` — remove `api_endpoint`, `effective_api_endpoint`, `DeviceHeader`
- Create: migration to remove fields

**Step 1: Remove from models.py**

In `backend/devices/models.py`:
- Remove `api_endpoint = models.URLField(blank=True, default="")` (line 20)
- Remove the entire `effective_api_endpoint` property (lines 36-45)
- Remove the entire `DeviceHeader` class (lines 48-61)

**Step 2: Create migration**

```bash
python manage.py makemigrations devices
```

This should generate a migration that removes the `api_endpoint` field and the `DeviceHeader` model.

**Step 3: Run migration and tests**

```bash
python manage.py migrate
python -m pytest backend/ -v --timeout=60
```

**Step 4: Fix any remaining references**

Grep for `api_endpoint`, `DeviceHeader`, `effective_api_endpoint`, and `headers` references across the codebase that still point to the old Device fields. Update or remove them.

Key files to check:
- `backend/devices/forms.py` — update or remove the old form
- `backend/devices/admin.py` — update admin registration
- Old device tests that reference `api_endpoint` directly on Device — these need updating to use config_source

**Step 5: Update existing Device tests**

The existing tests in `backend/devices/tests.py` that create devices with `api_endpoint=...` need updating. Devices that used `api_endpoint` should now use a config source. Update `DeviceModelTests`, `DeviceHeaderModelTests`, `DeviceAPITests` accordingly.

Key changes:
- Remove `DeviceHeaderModelTests` class entirely
- In `DeviceModelTests`, remove `test_effective_api_endpoint_*` tests (this logic moved to `ApiConfigSource`)
- In `DeviceAPITests`, update setUp to create devices with config sources
- Update `test_create_device` payloads to use `config_source` instead of `api_endpoint` + `headers`

**Step 6: Run full test suite**

```bash
python -m pytest backend/ -v --timeout=60
```

Expected: All tests PASS.

**Step 7: Commit**

```bash
git add backend/devices/
git commit -m "refactor: remove legacy api_endpoint, DeviceHeader, effective_api_endpoint"
```

---

### Task 14: Update Frontend Types

**Files:**
- Modify: `frontend/src/types/device.ts`

**Step 1: Update TypeScript types**

Replace `frontend/src/types/device.ts` with:

```typescript
// Config source types
export interface ApiConfigSourceData {
  source_type: "api";
  api_endpoint?: string;
  headers?: Record<string, string>;
  effective_api_endpoint?: string;
}

export interface GitConfigSourceData {
  source_type: "git";
  repo_url: string;
  branch: string;
  file_path: string;
}

export interface ManualConfigSourceData {
  source_type: "manual";
  config_text: string;
}

export type ConfigSourceData =
  | ApiConfigSourceData
  | GitConfigSourceData
  | ManualConfigSourceData;

export interface Device {
  id: number;
  name: string;
  hostname: string;
  enabled: boolean;
  config_source: ConfigSourceData | null;
  last_fetched_config: string;
  config_fetched_at: string | null;
  groups: number[];
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
  enabled: boolean;
  config_source?: ConfigSourceData | null;
  groups: number[];
}

export interface DeviceGroupFormData {
  name: string;
  description: string;
  devices: number[];
}

export interface TestConnectionResult {
  success: boolean;
  status_code?: number;
  content_length?: number;
  error?: string;
}
```

**Step 2: Commit**

```bash
git add frontend/src/types/device.ts
git commit -m "feat: update frontend device types for config sources"
```

---

### Task 15: Update Frontend Hooks

**Files:**
- Modify: `frontend/src/hooks/use-devices.ts`

**Step 1: Update hooks**

Modify `frontend/src/hooks/use-devices.ts` — the hooks mostly stay the same since the types handle the shape change. Key changes:

- `useFetchDeviceConfig` should POST (not GET) to `/devices/{id}/fetch-config/`
- Add `useFetchConfig` hook if the URL path changed

```typescript
export function useFetchDeviceConfig(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const response = await api.post<{ config: string }>(`/devices/${id}/fetch-config/`);
      return response.data.config;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["devices", id] });
    },
  });
}
```

**Step 2: Commit**

```bash
git add frontend/src/hooks/use-devices.ts
git commit -m "feat: update device hooks for config source API changes"
```

---

### Task 16: Rebuild Device Form Page

**Files:**
- Modify: `frontend/src/pages/devices/form.tsx`

**Step 1: Rewrite the form**

This is the largest frontend change. The form needs:

1. A radio group / segmented control for source type selection (API / Git / Manual)
2. Conditional fields that swap based on source type:
   - **API**: endpoint URL + dynamic key/value header rows
   - **Git**: repo URL, branch, file path
   - **Manual**: Monaco editor for config text
3. State management using `useState` for each source type's fields
4. Form submission builds the `config_source` payload based on selected type

Key imports to add:
- `import Editor from "@monaco-editor/react"` (Monaco editor — check existing import pattern in the project)
- Radio group component from shadcn/ui (check `frontend/src/components/ui/` for existing radio-group)

If `radio-group` doesn't exist yet, create it via:
```bash
cd /Users/aaronroth/Documents/netaudit/frontend
npx shadcn@latest add radio-group
```

The form state should track:
```typescript
const [sourceType, setSourceType] = useState<"api" | "git" | "manual">("api");
// API fields
const [apiEndpoint, setApiEndpoint] = useState("");
const [headers, setHeaders] = useState<{ key: string; value: string }[]>([]);
// Git fields
const [repoUrl, setRepoUrl] = useState("");
const [branch, setBranch] = useState("main");
const [filePath, setFilePath] = useState("");
// Manual field
const [configText, setConfigText] = useState("");
```

The `handleSubmit` function builds `config_source` based on `sourceType`:
```typescript
const configSource = sourceType === "api"
  ? { source_type: "api" as const, api_endpoint: apiEndpoint || undefined, headers: Object.fromEntries(headers.filter(h => h.key).map(h => [h.key, h.value])) }
  : sourceType === "git"
  ? { source_type: "git" as const, repo_url: repoUrl, branch, file_path: filePath }
  : { source_type: "manual" as const, config_text: configText };
```

When editing, the `useEffect` populating form state should read from `device.config_source` and set the appropriate source type + fields.

**Step 2: Verify the form renders correctly**

Start the dev server and manually verify the form works for each source type.

**Step 3: Commit**

```bash
git add frontend/src/pages/devices/form.tsx frontend/src/components/ui/
git commit -m "feat: rebuild device form with config source type selector"
```

---

### Task 17: Update Device Detail Page

**Files:**
- Modify: `frontend/src/pages/devices/detail.tsx`

**Step 1: Update the detail page**

Changes needed:
1. Replace the "API Endpoint" and "Effective Endpoint" fields with a "Configuration Source" card that shows source-type-specific info
2. Replace the "Headers" card (only show for API sources)
3. Add a "Fetch Config" button (POST to `/devices/{id}/fetch-config/`)
4. Show `last_fetched_config` in a read-only Monaco editor or code block
5. Show `config_fetched_at` timestamp
6. Hide "Test Connection" button for non-API sources

The config source card should show:
- **API**: Endpoint URL, effective endpoint, headers table
- **Git**: Repo URL, branch, file path
- **Manual**: "Manual entry" label

Add a "Fetch Config" button that calls `useFetchDeviceConfig(deviceId)` and displays the result.

Add a collapsible section showing `device.last_fetched_config` if non-empty, with a "Last fetched: {config_fetched_at}" timestamp.

**Step 2: Verify the page renders correctly**

Start the dev server and manually verify for each source type.

**Step 3: Commit**

```bash
git add frontend/src/pages/devices/detail.tsx
git commit -m "feat: update device detail page for config sources"
```

---

### Task 18: Update Device List Page

**Files:**
- Modify: `frontend/src/pages/devices/list.tsx`

**Step 1: Add source type column**

Add a new column to the devices table showing the config source type:

```typescript
{
  accessorKey: "config_source",
  header: "Config Source",
  cell: ({ row }) => {
    const source = row.original.config_source;
    if (!source) return <span className="text-muted-foreground">None</span>;
    const labels = { api: "API", git: "Git", manual: "Manual" };
    return <Badge variant="outline">{labels[source.source_type]}</Badge>;
  },
},
```

**Step 2: Commit**

```bash
git add frontend/src/pages/devices/list.tsx
git commit -m "feat: add config source type column to device list"
```

---

### Task 19: Final Integration Test + Cleanup

**Files:**
- All modified files

**Step 1: Run full backend test suite**

```bash
cd /Users/aaronroth/Documents/netaudit/backend
python -m pytest -v --timeout=60
```

Fix any remaining failures.

**Step 2: Run frontend build**

```bash
cd /Users/aaronroth/Documents/netaudit/frontend
npm run build
```

Fix any TypeScript errors.

**Step 3: Run frontend linter**

```bash
npm run lint
```

Fix any lint errors.

**Step 4: Manual smoke test**

1. Start backend: `python manage.py runserver`
2. Start frontend: `npm run dev`
3. Create a device with each source type (API, Git, Manual)
4. Edit a device and change its source type
5. Fetch config for a manual-source device
6. Verify device detail page displays correctly for each type

**Step 5: Final commit**

```bash
git add -A
git commit -m "fix: integration fixes and cleanup for config sources"
```
