# Config Sources Design

**Date:** 2026-03-01
**Status:** Approved

## Problem

Device running-configs (the text audited against rules) can currently only be fetched via a live HTTP API call. Users need flexibility to load configs from multiple source types: git repositories, manual paste, and (eventually) job runs.

## Requirements

- Each device has exactly one config source at a time
- Three source types implemented now: API endpoint, git repo, manual paste
- Architecture extensible for a future "job run" source type
- Config text stored persistently on the device (with on-demand refresh)
- Clean break from existing api_endpoint/DeviceHeader model — data migrated, old fields removed

## Architecture: Strategy Pattern with Separate Tables

Uses Django multi-table inheritance for type-safe, strongly-typed source models.

### Data Model

New `config_sources` Django app:

```
ConfigSource (base model)
├── source_type  CharField (choices: api, git, manual)
├── created_at   DateTimeField
├── updated_at   DateTimeField
│
├── ApiConfigSource (child, multi-table inheritance)
│   ├── api_endpoint  URLField
│   └── headers       JSONField (dict of key/value pairs)
│
├── GitConfigSource (child, multi-table inheritance)
│   ├── repo_url   URLField
│   ├── branch     CharField (default "main")
│   └── file_path  CharField
│
└── ManualConfigSource (child, multi-table inheritance)
    └── config_text  TextField
```

Device model changes:
- **Add:** `config_source` OneToOneField → ConfigSource (nullable, SET_NULL on delete)
- **Add:** `last_fetched_config` TextField (blank) — cached config text from most recent fetch
- **Add:** `config_fetched_at` DateTimeField (nullable) — timestamp of most recent fetch
- **Remove:** `api_endpoint` field (migrated to ApiConfigSource)
- **Remove:** `DeviceHeader` model (migrated to ApiConfigSource.headers JSONField)
- **Remove:** `effective_api_endpoint` property (moved to ApiConfigSource)

### ApiConfigSource: Effective Endpoint Logic

ApiConfigSource retains the current fallback behavior:

```python
@property
def effective_api_endpoint(self):
    if self.api_endpoint:
        return self.api_endpoint
    site = SiteSettings.load()
    if site.default_api_endpoint:
        base = site.default_api_endpoint.rstrip("/")
        device = self.configsource_ptr.device
        return f"{base}/{device.name}"
    return ""
```

## Config Fetching Layer

`config_sources/fetchers.py` — strategy-based dispatch:

```python
def fetch_config(device) -> str:
    source = device.config_source
    if source is None:
        raise ValueError(f"Device '{device.name}' has no config source configured")

    match source.source_type:
        case "api":    text = _fetch_api(source.apiconfigsource)
        case "git":    text = _fetch_git(source.gitconfigsource)
        case "manual": text = _fetch_manual(source.manualconfigsource)

    device.last_fetched_config = text
    device.config_fetched_at = now()
    device.save(update_fields=["last_fetched_config", "config_fetched_at"])
    return text
```

### Fetcher Implementations

**API fetcher:** HTTP GET to effective endpoint with headers dict. Same as current `_fetch_config` in `audits/services.py`.

**Git fetcher:** Uses `subprocess` with `git` CLI. Persistent cache directory (configurable, default `/tmp/netaudit-git-cache/`). First fetch clones the repo; subsequent fetches do `git fetch && git checkout origin/<branch>`. Reads file at `file_path` relative to repo root.

**Manual fetcher:** Returns `source.config_text` directly (already stored in DB).

### Integration with Audits

`audits/services.py` `_fetch_config` is replaced with a call to `config_sources.fetchers.fetch_config`. The audit flow remains:

1. PENDING → FETCHING_CONFIG → call `fetch_config(device)` → RUNNING_RULES → COMPLETED/FAILED
2. `audit_run.config_snapshot` still stores the config text used for that specific run

## REST API Design

Config source is managed inline on the device — no separate endpoints.

### Device Create/Update Request

```json
{
  "name": "router-1",
  "hostname": "10.0.0.1",
  "enabled": true,
  "groups": [1, 2],
  "config_source": {
    "source_type": "api",
    "api_endpoint": "https://device-api.internal/router-1/config",
    "headers": {"Authorization": "Bearer xxx"}
  }
}
```

```json
{
  "config_source": {
    "source_type": "git",
    "repo_url": "https://github.com/org/configs.git",
    "branch": "main",
    "file_path": "routers/router-1.cfg"
  }
}
```

```json
{
  "config_source": {
    "source_type": "manual",
    "config_text": "hostname router-1\ninterface GigabitEthernet0/0\n..."
  }
}
```

### Device Response

Includes config source data, `last_fetched_config`, and `config_fetched_at`.

### Serialization

Discriminated `ConfigSourceSerializer` validates fields based on `source_type`:
- `source_type` is required
- Only fields relevant to the selected type are accepted/required
- Extra fields for other types are rejected

Device serializer handles nested create/update of config source (create new, replace existing on type change).

### Device Actions

- `POST /devices/{id}/fetch-config/` — triggers fresh fetch from configured source, returns config text, updates `last_fetched_config`
- `POST /devices/{id}/test-connection/` — only valid for API source type (tests HTTP connectivity)

## Frontend UX

### Device Form

Source type selector (radio buttons or segmented control) in a "Configuration Source" section:

```
┌─ Configuration Source ────────────────────────┐
│  Source Type: ( ) API  (•) Git  ( ) Manual    │
│                                               │
│  [Conditional fields based on selection]      │
│  Repository URL: [________________________]   │
│  Branch:         [main____________________]   │
│  File Path:      [configs/router-1.cfg____]   │
└───────────────────────────────────────────────┘
```

- **API:** Endpoint URL + dynamic key/value header inputs
- **Git:** Repo URL, branch, file path
- **Manual:** Monaco editor (already a project dependency) for config text

### Device Detail Page

Shows current config source info and a "Fetch Config" button for refreshing. For manual source the fetch button is hidden (config is already inline). Displays `last_fetched_config` and `config_fetched_at` when available.

## Migration Strategy

1. Create `config_sources` app with new models
2. Add `config_source`, `last_fetched_config`, `config_fetched_at` to Device
3. Data migration: for each device with `api_endpoint` or headers, create an `ApiConfigSource` and link it
4. Remove `api_endpoint` from Device model
5. Remove `DeviceHeader` model
6. Update all references (views, serializers, services, frontend)

Clean break — no deprecated fields retained.

## Future Extensibility

Adding a new source type (e.g. "job_run") requires:
1. New `JobRunConfigSource(ConfigSource)` model + migration
2. New `_fetch_job_run()` fetcher function
3. Add case to `fetch_config()` dispatch
4. Add source_type choice
5. Add frontend form fields for the new type
