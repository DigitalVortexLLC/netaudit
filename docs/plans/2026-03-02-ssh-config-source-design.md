# SSH Config Source Design

**Date:** 2026-03-02
**Status:** Approved

## Problem

Device running-configs can currently only be fetched via HTTP API calls. Many network devices expose their configuration only via SSH (show running-config, display current-configuration, etc.). Users need the ability to pull configs directly from devices over SSH using netmiko.

## Requirements

- SSH becomes a new config source type alongside API, Git, and Manual
- Uses netmiko for SSH transport
- A reference model for netmiko device types (vendor driver + default dump command)
- Per-device prompt overrides passed to netmiko's `send_command()`
- Encrypted credential storage in the database
- API endpoint to trigger an async config fetch for a device
- Integrates with the existing config source multi-table inheritance pattern

## Architecture

Builds on the ConfigSource multi-table inheritance design from `2026-03-01-config-sources-design.md`. Adds two new models and an SSH fetcher.

### Data Model

#### NetmikoDeviceType (new, standalone reference model)

```python
class NetmikoDeviceType(models.Model):
    name = models.CharField(max_length=255, unique=True)        # "Cisco IOS"
    driver = models.CharField(max_length=100)                   # "cisco_ios"
    default_command = models.CharField(max_length=500)          # "show running-config"
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
```

Reusable across devices. Users create entries for each vendor platform they manage.

#### SshConfigSource (child of ConfigSource, multi-table inheritance)

```python
class SshConfigSource(ConfigSource):
    netmiko_device_type = models.ForeignKey(
        NetmikoDeviceType, on_delete=models.PROTECT
    )
    hostname = models.CharField(max_length=255, blank=True)     # defaults to device.hostname
    port = models.IntegerField(default=22)
    username = encrypt(models.CharField(max_length=255))
    password = encrypt(models.CharField(max_length=255, blank=True))
    ssh_key = encrypt(models.TextField(blank=True))
    command_override = models.CharField(max_length=500, blank=True)
    prompt_overrides = models.JSONField(default=dict, blank=True)
    timeout = models.IntegerField(default=30)
```

Field details:

- **netmiko_device_type**: FK to the driver/command reference. PROTECT prevents deleting a type that's in use.
- **hostname**: SSH target. If blank, falls back to `device.hostname`.
- **username/password/ssh_key**: Encrypted via `django-encrypted-model-fields` (Fernet, keyed from `SECRET_KEY`).
- **command_override**: If set, used instead of `netmiko_device_type.default_command`.
- **prompt_overrides**: JSONField dict passed as kwargs to `send_command()`. Supports netmiko options like `expect_string`, `strip_prompt`, `strip_command`, `read_timeout`, `global_delay_factor`.
- **timeout**: Connection timeout in seconds.

### prompt_overrides Schema

```json
{
    "expect_string": "router#",
    "strip_prompt": false,
    "strip_command": true,
    "read_timeout": 60
}
```

All keys are optional. The dict is unpacked directly into `conn.send_command(command, **prompt_overrides)`.

## SSH Fetcher

Integrates into the config source fetcher dispatch (`config_sources/fetchers.py`):

```python
def _fetch_ssh(ssh_source, device):
    from netmiko import ConnectHandler

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

    if ssh_source.ssh_key:
        connect_params["use_keys"] = True
        connect_params["key_file"] = _write_temp_key(ssh_source.ssh_key)

    try:
        with ConnectHandler(**connect_params) as conn:
            send_kwargs = {}
            if ssh_source.prompt_overrides:
                send_kwargs.update(ssh_source.prompt_overrides)
            output = conn.send_command(command, **send_kwargs)
        return output
    finally:
        if "key_file" in connect_params:
            _cleanup_temp_key(connect_params["key_file"])
```

SSH key handling: written to a temporary file with restrictive permissions (0o600), cleaned up in a finally block.

### Integration with fetch_config dispatch

```python
def fetch_config(device):
    source = device.config_source
    if source is None:
        raise ValueError(f"Device '{device.name}' has no config source configured")

    match source.source_type:
        case "api":    text = _fetch_api(source.apiconfigsource)
        case "git":    text = _fetch_git(source.gitconfigsource)
        case "manual": text = _fetch_manual(source.manualconfigsource)
        case "ssh":    text = _fetch_ssh(source.sshconfigsource, device)

    device.last_fetched_config = text
    device.config_fetched_at = now()
    device.save(update_fields=["last_fetched_config", "config_fetched_at"])
    return text
```

## REST API

### NetmikoDeviceType CRUD

`/api/v1/netmiko-device-types/` — standard ModelViewSet.

```
GET    /api/v1/netmiko-device-types/          # List all
POST   /api/v1/netmiko-device-types/          # Create
GET    /api/v1/netmiko-device-types/{id}/     # Detail
PUT    /api/v1/netmiko-device-types/{id}/     # Update
DELETE /api/v1/netmiko-device-types/{id}/     # Delete (blocked if in use via PROTECT)
```

Request/response:

```json
{
    "id": 1,
    "name": "Cisco IOS",
    "driver": "cisco_ios",
    "default_command": "show running-config",
    "description": "Cisco IOS and IOS-XE devices"
}
```

### SSH Config Source (inline on Device)

Managed inline when creating/updating a device, following the ConfigSource design:

```json
{
    "name": "router-1",
    "hostname": "10.0.0.1",
    "enabled": true,
    "config_source": {
        "source_type": "ssh",
        "netmiko_device_type": 1,
        "hostname": "",
        "port": 22,
        "username": "admin",
        "password": "secret",
        "ssh_key": "",
        "command_override": "",
        "prompt_overrides": {"expect_string": "router#"},
        "timeout": 30
    }
}
```

Password/ssh_key are write-only — not returned in GET responses (serializer excludes them or returns masked values).

### Trigger Backup (Async)

`POST /api/v1/devices/{id}/fetch-config/` — existing endpoint from config sources design.

For SSH sources, this queues the fetch as a Django-Q2 async task:

1. Returns `202 Accepted` with `{"task_id": "...", "status": "queued"}`
2. Django-Q2 worker executes `_fetch_ssh()` in the background
3. On success: updates `device.last_fetched_config` and `device.config_fetched_at`
4. On failure: stores error message on the device

Client polls `GET /api/v1/devices/{id}/` and checks `config_fetched_at` for completion.

## Frontend

### Device Form — SSH Source Fields

```
┌─ Configuration Source ──────────────────────────────────┐
│  Source Type: ( ) API  ( ) Git  ( ) Manual  (•) SSH     │
│                                                         │
│  Netmiko Device Type: [Cisco IOS____________▼]          │
│  SSH Hostname:        [________________________] (opt)  │
│  Port:                [22_____]                         │
│  Username:            [________________________]        │
│  Password:            [••••••••_______________]         │
│  SSH Key:             [textarea________________]        │
│  Command Override:    [________________________] (opt)  │
│  Prompt Overrides:    [JSON editor_____________] (opt)  │
│  Timeout:             [30_____]                         │
└─────────────────────────────────────────────────────────┘
```

- Netmiko Device Type is a searchable dropdown
- SSH Hostname shows placeholder "Defaults to device hostname"
- Password field is masked, only shown on edit if already set
- Prompt Overrides uses a simple JSON key-value editor or raw JSON textarea

### NetmikoDeviceType Management Pages

- List page: table with name, driver, default command, usage count
- Create/edit form: name, driver (with helper text listing common drivers), default command, description
- Linked from sidebar or settings area

### Device Detail — Fetch Button

"Fetch Config" button triggers `POST /fetch-config/`. Shows spinner while queued, updates when config arrives.

## Error Handling

- **NetmikoTimeoutException**: "SSH connection timed out after {timeout}s to {host}:{port}"
- **NetmikoAuthenticationException**: "SSH authentication failed for {username}@{host}:{port}"
- **Connection refused**: "SSH connection refused by {host}:{port}"
- **Command errors**: If output is empty, store warning but don't fail
- **Encryption key change**: If `SECRET_KEY` rotates, encrypted fields become unreadable. Documented limitation.

## Dependencies

Add to `backend/requirements.txt`:

```
netmiko>=4.0,<5.0
django-encrypted-model-fields>=0.6,<1.0
```

`netmiko` pulls in `paramiko` as a transitive dependency.

## Future Considerations

- **Credential profiles**: Extract credentials into a shared model if many devices use the same creds
- **SSH key management**: Support key passphrases
- **Bulk backup**: Trigger fetch-config for all SSH devices in a group
- **Config diff**: Compare current config against previous backup
