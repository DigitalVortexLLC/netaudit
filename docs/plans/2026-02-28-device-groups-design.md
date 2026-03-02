# Device Groups Design

## Problem

Devices are standalone entities with no organizational structure. Users need to group devices for three purposes: organizational filtering, assigning rules to groups of devices, and running bulk audits.

## Requirements

- Many-to-many: a device can belong to multiple groups
- Flat: no nested hierarchy
- Rules scoping: rules can target a group (applies to all member devices)
- Bulk audits: trigger audits for all enabled devices in a group
- Union semantics: a device gets rules from all its groups combined
- Organizational: filter and view devices by group

## Design

### Data Model

**New `DeviceGroup` model** in `devices/models.py`:

| Field       | Type                        | Notes                |
|-------------|-----------------------------|----------------------|
| name        | CharField(255, unique=True) | Group identifier     |
| description | TextField(blank=True)       | Optional description |
| created_at  | DateTimeField(auto_now_add) |                      |
| updated_at  | DateTimeField(auto_now)     |                      |

**M2M on Device**: `groups = ManyToManyField(DeviceGroup, related_name="devices", blank=True)`

Creates two tables: `devices_devicegroup` and auto-generated `devices_device_groups` join table.

### Rules Scoping

Add optional `group` FK on both `SimpleRule` and `CustomRule`, same nullable pattern as existing `device` FK. A rule targets one of:

- A specific device (`device` set, `group` null)
- A group (`group` set, `device` null)
- All devices (both null — existing global behavior)

In `audits/services.py`, rule queries expand to include `Q(group__in=device.groups.all())`.

### API (DRF)

New `DeviceGroupViewSet` at `/api/v1/groups/`:

- Standard CRUD
- `POST /api/v1/groups/{id}/run_audit/` — fans out `enqueue_audit()` per enabled device
- Filter/search support

Device serializer: add `groups` field (list of group IDs).
Rule serializers: add `group` field.
Rule viewsets: add `group` to `filterset_fields`.

### Frontend (HTML + HTMX)

- Group list page (`/groups/`) with device count column
- Group create/edit form (name, description, device multi-select)
- Group detail page (members, rules, "Run Audit on Group" button)
- Device list: show group badges
- Device detail: show group membership
- Device form: add group multi-select
- Rule forms: add group dropdown alongside device dropdown

### Audit Execution

No new audit model. `run_group_audit(group_id)` iterates enabled devices in the group and calls `enqueue_audit()` for each. Each device gets its own `AuditRun`.
