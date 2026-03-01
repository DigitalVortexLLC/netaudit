# Config Gather Model Design

**Date:** 2026-03-01

## Problem

Config gathering is tightly coupled to the Device model via `api_endpoint` (URL field) and `DeviceHeader` (per-device HTTP headers), with a site-wide fallback in `SiteSettings.default_api_endpoint`. This limits the system to HTTP GET and makes it hard to support other transport methods (SSH, SNMP, etc.).

## Solution

Introduce a standalone, reusable `ConfigGather` model that encapsulates how to fetch configuration from a device. Uses a `gather_type` choice field with a `config` JSONField for transport-specific settings. A handler registry pattern makes adding new transports trivial.

## Data Model

### ConfigGather (new, in `devices` app)

```python
class ConfigGather(models.Model):
    GATHER_TYPES = [
        ("http", "HTTP/REST"),
    ]

    name        = CharField(max_length=255, unique=True)
    gather_type = CharField(max_length=50, choices=GATHER_TYPES, default="http")
    config      = JSONField(default=dict)
    created_at  = DateTimeField(auto_now_add=True)
    updated_at  = DateTimeField(auto_now=True)
```

### HTTP config schema (in `config` JSONField)

```json
{
  "url": "https://api.example.com/configs/{device_name}",
  "method": "GET",
  "headers": {"Authorization": "Bearer xxx"},
  "timeout": 30,
  "verify_ssl": true
}
```

`{device_name}` is substituted at fetch time with `device.name`.

### Changes to existing models

- **Device**: Remove `api_endpoint`. Add `config_gather = FK(ConfigGather, null=True, blank=True)`.
- **DeviceGroup**: Add `config_gather = FK(ConfigGather, null=True, blank=True)`.
- **SiteSettings**: Remove `default_api_endpoint`. Add `default_config_gather = FK(ConfigGather, null=True, blank=True)`.
- **DeviceHeader**: Remove entirely. Headers move into ConfigGather's `config` JSON.

### Resolution order (on Device)

```python
@property
def effective_config_gather(self):
    if self.config_gather:
        return self.config_gather
    for group in self.groups.all():
        if group.config_gather:
            return group.config_gather
    site = SiteSettings.load()
    return site.default_config_gather  # may be None
```

Priority: Device > Group > Site default.

## Fetch Execution Layer

### Handler registry

```python
# devices/gather_handlers.py
GATHER_HANDLERS = {}

def register_handler(gather_type):
    def decorator(fn):
        GATHER_HANDLERS[gather_type] = fn
        return fn
    return decorator

@register_handler("http")
def http_handler(config_gather, device):
    cfg = config_gather.config
    url = cfg["url"].replace("{device_name}", device.name)
    method = cfg.get("method", "GET")
    headers = cfg.get("headers", {})
    timeout = cfg.get("timeout", 30)
    verify = cfg.get("verify_ssl", True)
    response = requests.request(method, url, headers=headers, timeout=timeout, verify=verify)
    response.raise_for_status()
    return response.text
```

### Audit service changes

`_fetch_config(device)` uses `device.effective_config_gather` and dispatches to the registered handler.

### Validation

Each handler type defines required keys. Validated in `ConfigGather.clean()` and form validation. HTTP requires `url` at minimum.

## UI & API

### CRUD

- Sidebar entry: "Config Gatherers"
- List/create/detail/edit/delete pages following existing patterns
- Form: name, gather type dropdown, dynamic transport-specific fields
- List: shows name, type, usage count
- Detail: shows config and lists referencing devices/groups/site default

### DRF API

`/api/v1/config-gatherers/` — standard ModelViewSet with config validation.

### Assignment changes

- **Device form**: `config_gather` dropdown replaces `api_endpoint` + headers formset
- **DeviceGroup form**: Add `config_gather` dropdown
- **Settings page**: `default_config_gather` dropdown replaces `default_api_endpoint`
- **Device detail**: Shows effective config gather with inheritance badge

### Test connection

Uses ConfigGather handler instead of raw HTTP GET.

## Data Migration

1. For each device with `api_endpoint` or headers: create a ConfigGather, link to device
2. If `SiteSettings.default_api_endpoint` is set: create a ConfigGather with `{base_url}/{device_name}` URL pattern, assign as site default
3. Remove old fields (`api_endpoint`, `DeviceHeader`, `default_api_endpoint`)
