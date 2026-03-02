# Device Groups Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a DeviceGroup model with M2M relationship to Device, enabling organizational grouping, group-scoped rules, and bulk group audits.

**Architecture:** New `DeviceGroup` model in the `devices` app with `ManyToManyField` on `Device`. Rules gain an optional `group` FK alongside the existing `device` FK. Audit rule-gathering queries expand to include group-scoped rules via union. A new `DeviceGroupViewSet` provides CRUD + bulk audit trigger.

**Tech Stack:** Django 5.1, DRF, HTMX, PostgreSQL, django-filter

---

### Task 1: DeviceGroup Model and Migration

**Files:**
- Modify: `backend/devices/models.py`
- Test: `backend/devices/tests.py`

**Step 1: Write failing tests for DeviceGroup model**

Add to `backend/devices/tests.py`:

```python
from .models import Device, DeviceGroup, DeviceHeader


class DeviceGroupModelTests(TestCase):
    """Tests for the DeviceGroup model."""

    def test_create_group(self):
        group = DeviceGroup.objects.create(
            name="Edge Routers",
            description="All edge routers",
        )
        self.assertEqual(group.name, "Edge Routers")
        self.assertEqual(group.description, "All edge routers")
        self.assertIsNotNone(group.created_at)
        self.assertIsNotNone(group.updated_at)

    def test_group_str(self):
        group = DeviceGroup.objects.create(name="Core Switches")
        self.assertEqual(str(group), "Core Switches")

    def test_group_unique_name(self):
        DeviceGroup.objects.create(name="unique-group")
        with self.assertRaises(IntegrityError):
            DeviceGroup.objects.create(name="unique-group")

    def test_group_ordering(self):
        DeviceGroup.objects.create(name="Zebra")
        DeviceGroup.objects.create(name="Alpha")
        groups = list(DeviceGroup.objects.values_list("name", flat=True))
        self.assertEqual(groups, ["Alpha", "Zebra"])

    def test_group_description_blank(self):
        group = DeviceGroup.objects.create(name="No Desc")
        self.assertEqual(group.description, "")


class DeviceGroupMembershipTests(TestCase):
    """Tests for the M2M relationship between Device and DeviceGroup."""

    def setUp(self):
        self.device1 = Device.objects.create(
            name="switch-01",
            hostname="switch-01.local",
            api_endpoint="https://switch-01.local/api",
        )
        self.device2 = Device.objects.create(
            name="switch-02",
            hostname="switch-02.local",
            api_endpoint="https://switch-02.local/api",
        )
        self.group = DeviceGroup.objects.create(name="Switches")

    def test_add_device_to_group(self):
        self.device1.groups.add(self.group)
        self.assertIn(self.group, self.device1.groups.all())
        self.assertIn(self.device1, self.group.devices.all())

    def test_device_multiple_groups(self):
        group2 = DeviceGroup.objects.create(name="Datacenter A")
        self.device1.groups.add(self.group, group2)
        self.assertEqual(self.device1.groups.count(), 2)

    def test_group_multiple_devices(self):
        self.group.devices.add(self.device1, self.device2)
        self.assertEqual(self.group.devices.count(), 2)

    def test_remove_device_from_group(self):
        self.device1.groups.add(self.group)
        self.device1.groups.remove(self.group)
        self.assertEqual(self.device1.groups.count(), 0)

    def test_delete_group_does_not_delete_devices(self):
        self.device1.groups.add(self.group)
        self.group.delete()
        self.assertTrue(Device.objects.filter(pk=self.device1.pk).exists())
        self.assertEqual(self.device1.groups.count(), 0)

    def test_delete_device_does_not_delete_group(self):
        self.device1.groups.add(self.group)
        self.device1.delete()
        self.assertTrue(DeviceGroup.objects.filter(pk=self.group.pk).exists())
        self.assertEqual(self.group.devices.count(), 0)
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest devices/tests.py -k "DeviceGroup" -v`
Expected: ImportError — `DeviceGroup` does not exist

**Step 3: Implement DeviceGroup model**

In `backend/devices/models.py`, add before the `Device` class:

```python
class DeviceGroup(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
```

Add `groups` field to the `Device` model:

```python
groups = models.ManyToManyField(
    "DeviceGroup",
    related_name="devices",
    blank=True,
)
```

**Step 4: Create and run migration**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py makemigrations devices && python manage.py migrate`
Expected: Migration created and applied successfully

**Step 5: Run tests to verify they pass**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest devices/tests.py -k "DeviceGroup" -v`
Expected: All DeviceGroup tests PASS

**Step 6: Commit**

```bash
git add backend/devices/models.py backend/devices/tests.py backend/devices/migrations/
git commit -m "feat: add DeviceGroup model with M2M relationship to Device"
```

---

### Task 2: DeviceGroup API (Serializer, ViewSet, URLs)

**Files:**
- Modify: `backend/devices/serializers.py`
- Modify: `backend/devices/views.py`
- Modify: `backend/devices/urls.py`
- Test: `backend/devices/tests.py`

**Step 1: Write failing tests for DeviceGroup API**

Add to `backend/devices/tests.py`:

```python
from .models import Device, DeviceGroup, DeviceHeader


class DeviceGroupAPITests(APITestCase):
    """Tests for the DeviceGroup REST API endpoints."""

    def setUp(self):
        self.group = DeviceGroup.objects.create(
            name="Edge Routers",
            description="All edge routers",
        )
        self.list_url = reverse("devicegroup-list")
        self.detail_url = reverse("devicegroup-detail", kwargs={"pk": self.group.pk})

    def test_list_groups(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Edge Routers")

    def test_list_groups_includes_device_count(self):
        device = Device.objects.create(
            name="d1", hostname="d1.local", api_endpoint="https://d1.local/api",
        )
        device.groups.add(self.group)
        response = self.client.get(self.list_url)
        self.assertEqual(response.data["results"][0]["device_count"], 1)

    def test_create_group(self):
        data = {"name": "Core Switches", "description": "Core layer"}
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DeviceGroup.objects.count(), 2)

    def test_create_group_duplicate_name_fails(self):
        data = {"name": "Edge Routers"}
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_group(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Edge Routers")
        self.assertIn("devices", response.data)

    def test_retrieve_group_includes_device_ids(self):
        device = Device.objects.create(
            name="d1", hostname="d1.local", api_endpoint="https://d1.local/api",
        )
        device.groups.add(self.group)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.data["devices"], [device.pk])

    def test_update_group(self):
        data = {"name": "Updated Name", "description": "Updated desc"}
        response = self.client.put(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        self.assertEqual(self.group.name, "Updated Name")

    def test_partial_update_group(self):
        response = self.client.patch(
            self.detail_url, {"description": "New desc"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.group.refresh_from_db()
        self.assertEqual(self.group.description, "New desc")

    def test_delete_group(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(DeviceGroup.objects.filter(pk=self.group.pk).exists())

    def test_delete_group_not_found(self):
        url = reverse("devicegroup-detail", kwargs={"pk": 99999})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest devices/tests.py -k "DeviceGroupAPI" -v`
Expected: FAIL — reverse for `devicegroup-list` not found

**Step 3: Implement DeviceGroup serializer**

In `backend/devices/serializers.py`, add:

```python
from .models import Device, DeviceGroup, DeviceHeader


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
```

**Step 4: Implement DeviceGroup ViewSet**

In `backend/devices/views.py`, add:

```python
from .models import Device, DeviceGroup
from .serializers import DeviceGroupSerializer, DeviceSerializer


class DeviceGroupViewSet(viewsets.ModelViewSet):
    queryset = DeviceGroup.objects.prefetch_related("devices").all()
    serializer_class = DeviceGroupSerializer
    search_fields = ["name", "description"]
```

**Step 5: Register route**

In `backend/devices/urls.py`, add:

```python
from .views import DeviceGroupViewSet, DeviceViewSet

router.register("groups", DeviceGroupViewSet)
```

**Step 6: Run tests to verify they pass**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest devices/tests.py -k "DeviceGroupAPI" -v`
Expected: All PASS

**Step 7: Update DeviceSerializer to include groups**

In `backend/devices/serializers.py`, add `groups` to DeviceSerializer:

```python
class DeviceSerializer(serializers.ModelSerializer):
    headers = DeviceHeaderSerializer(many=True, required=False)
    groups = serializers.PrimaryKeyRelatedField(
        many=True, queryset=DeviceGroup.objects.all(), required=False,
    )

    class Meta:
        model = Device
        fields = [
            "id",
            "name",
            "hostname",
            "api_endpoint",
            "enabled",
            "headers",
            "groups",
            "created_at",
            "updated_at",
        ]
```

Update the `create` and `update` methods to handle `groups`:

In `create`:
```python
groups_data = validated_data.pop("groups", [])
device = Device.objects.create(**validated_data)
# ... existing header logic ...
if groups_data:
    device.groups.set(groups_data)
return device
```

In `update`:
```python
groups_data = validated_data.pop("groups", None)
# ... existing header logic ...
if groups_data is not None:
    instance.groups.set(groups_data)
return instance
```

**Step 8: Run full device test suite**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest devices/tests.py -v`
Expected: All PASS

**Step 9: Commit**

```bash
git add backend/devices/serializers.py backend/devices/views.py backend/devices/urls.py backend/devices/tests.py
git commit -m "feat: add DeviceGroup API with CRUD endpoints and device membership"
```

---

### Task 3: Add Group FK to Rule Models

**Files:**
- Modify: `backend/rules/models.py`
- Modify: `backend/rules/serializers.py`
- Modify: `backend/rules/views.py`
- Modify: `backend/rules/forms.py`
- Test: `backend/rules/tests.py`

**Step 1: Write failing tests for group FK on rules**

Add to `backend/rules/tests.py`:

```python
from devices.models import Device, DeviceGroup


class SimpleRuleGroupTests(TestCase):
    """Tests for SimpleRule group FK."""

    def test_group_fk_nullable(self):
        rule = SimpleRule.objects.create(
            name="Global Rule",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="ntp",
        )
        self.assertIsNone(rule.group)

    def test_group_fk_assigned(self):
        group = DeviceGroup.objects.create(name="Routers")
        rule = SimpleRule.objects.create(
            name="Router Rule",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="ntp",
            group=group,
        )
        self.assertEqual(rule.group, group)

    def test_group_cascade_delete(self):
        group = DeviceGroup.objects.create(name="Temp")
        SimpleRule.objects.create(
            name="Temp Rule",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="x",
            group=group,
        )
        group.delete()
        self.assertEqual(SimpleRule.objects.count(), 0)

    def test_related_name(self):
        group = DeviceGroup.objects.create(name="Switches")
        SimpleRule.objects.create(
            name="Switch Rule",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="vlan",
            group=group,
        )
        self.assertEqual(group.simple_rules.count(), 1)


class CustomRuleGroupTests(TestCase):
    """Tests for CustomRule group FK."""

    def test_group_fk_nullable(self):
        rule = CustomRule.objects.create(
            name="Global Custom",
            filename="test_global.py",
            content="def test_x(): pass",
        )
        self.assertIsNone(rule.group)

    def test_group_fk_assigned(self):
        group = DeviceGroup.objects.create(name="Routers")
        rule = CustomRule.objects.create(
            name="Router Custom",
            filename="test_router.py",
            content="def test_x(): pass",
            group=group,
        )
        self.assertEqual(rule.group, group)

    def test_related_name(self):
        group = DeviceGroup.objects.create(name="Switches")
        CustomRule.objects.create(
            name="Switch Custom",
            filename="test_switch.py",
            content="def test_x(): pass",
            group=group,
        )
        self.assertEqual(group.custom_rules.count(), 1)
```

And API tests:

```python
class SimpleRuleGroupAPITests(APITestCase):
    """Tests for SimpleRule API with group FK."""

    def test_create_with_group(self):
        group = DeviceGroup.objects.create(name="Routers")
        url = reverse("simplerule-list")
        payload = {
            "name": "Group Rule",
            "rule_type": "must_contain",
            "pattern": "ntp",
            "severity": "high",
            "enabled": True,
            "group": group.pk,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["group"], group.pk)

    def test_filter_by_group(self):
        group = DeviceGroup.objects.create(name="Routers")
        SimpleRule.objects.create(
            name="Group Rule",
            rule_type="must_contain",
            pattern="ntp",
            group=group,
        )
        SimpleRule.objects.create(
            name="Global Rule",
            rule_type="must_contain",
            pattern="dns",
        )
        url = reverse("simplerule-list")
        response = self.client.get(url, {"group": group.pk})
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Group Rule")


class CustomRuleGroupAPITests(APITestCase):
    """Tests for CustomRule API with group FK."""

    def test_create_with_group(self):
        group = DeviceGroup.objects.create(name="Switches")
        url = reverse("customrule-list")
        payload = {
            "name": "Group Custom",
            "filename": "test_group.py",
            "content": "def test_x(): pass",
            "severity": "medium",
            "enabled": True,
            "group": group.pk,
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["group"], group.pk)

    def test_filter_by_group(self):
        group = DeviceGroup.objects.create(name="Switches")
        CustomRule.objects.create(
            name="Group Custom",
            filename="test_sw.py",
            content="def test_x(): pass",
            group=group,
        )
        CustomRule.objects.create(
            name="Global Custom",
            filename="test_gl.py",
            content="def test_x(): pass",
        )
        url = reverse("customrule-list")
        response = self.client.get(url, {"group": group.pk})
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Group Custom")
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest rules/tests.py -k "Group" -v`
Expected: FAIL — `group` field doesn't exist

**Step 3: Add group FK to SimpleRule and CustomRule**

In `backend/rules/models.py`, add to both `SimpleRule` and `CustomRule`:

```python
group = models.ForeignKey(
    "devices.DeviceGroup",
    on_delete=models.CASCADE,
    related_name="simple_rules",  # or "custom_rules" for CustomRule
    null=True,
    blank=True,
    help_text="If set, rule applies to all devices in this group",
)
```

**Step 4: Create and run migration**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py makemigrations rules && python manage.py migrate`

**Step 5: Update rule serializers to include group**

The serializers use `fields = "__all__"` so the `group` field will be automatically included.

**Step 6: Update rule viewsets filterset_fields to include group**

In `backend/rules/views.py`:

```python
class SimpleRuleViewSet(viewsets.ModelViewSet):
    filterset_fields = ["device", "group", "enabled", "severity", "rule_type"]

class CustomRuleViewSet(viewsets.ModelViewSet):
    filterset_fields = ["device", "group", "enabled", "severity"]
```

**Step 7: Update rule forms to include group**

In `backend/rules/forms.py`:

```python
class SimpleRuleForm(forms.ModelForm):
    class Meta:
        model = SimpleRule
        fields = [
            "name", "description", "rule_type", "pattern",
            "severity", "enabled", "device", "group",
        ]

class CustomRuleForm(forms.ModelForm):
    class Meta:
        model = CustomRule
        fields = [
            "name", "description", "filename", "content",
            "severity", "enabled", "device", "group",
        ]
```

**Step 8: Run tests to verify they pass**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest rules/tests.py -v`
Expected: All PASS

**Step 9: Commit**

```bash
git add backend/rules/models.py backend/rules/serializers.py backend/rules/views.py backend/rules/forms.py backend/rules/tests.py backend/rules/migrations/
git commit -m "feat: add group FK to SimpleRule and CustomRule models"
```

---

### Task 4: Expand Audit Service to Include Group-Scoped Rules

**Files:**
- Modify: `backend/audits/services.py`
- Test: `backend/audits/tests.py`

**Step 1: Write failing tests for group-scoped rule gathering**

Add to `backend/audits/tests.py`:

```python
from devices.models import Device, DeviceGroup
from rules.models import CustomRule, SimpleRule


class GroupScopedRuleGatheringTests(AuditFixtureMixin, TestCase):
    """Tests that audit service gathers rules from device groups."""

    def setUp(self):
        self.device = self.create_device()
        self.group = DeviceGroup.objects.create(name="Edge Routers")
        self.device.groups.add(self.group)

    def test_gather_simple_rules_from_group(self):
        """A simple rule scoped to a group should apply to devices in that group."""
        group_rule = SimpleRule.objects.create(
            name="Group NTP",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="ntp server",
            group=self.group,
            enabled=True,
        )
        from audits.services import _gather_simple_rules
        rules = _gather_simple_rules(self.device)
        rule_ids = [r["id"] for r in rules]
        self.assertIn(group_rule.id, rule_ids)

    def test_gather_simple_rules_excludes_other_groups(self):
        """A simple rule scoped to a different group should NOT apply."""
        other_group = DeviceGroup.objects.create(name="Other")
        SimpleRule.objects.create(
            name="Other Group Rule",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="ntp",
            group=other_group,
            enabled=True,
        )
        from audits.services import _gather_simple_rules
        rules = _gather_simple_rules(self.device)
        self.assertEqual(len(rules), 0)

    def test_gather_simple_rules_union_device_group_global(self):
        """Device gets rules from its own FK, all its groups, and global."""
        device_rule = SimpleRule.objects.create(
            name="Device Rule",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="hostname",
            device=self.device,
            enabled=True,
        )
        group_rule = SimpleRule.objects.create(
            name="Group Rule",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="ntp",
            group=self.group,
            enabled=True,
        )
        global_rule = SimpleRule.objects.create(
            name="Global Rule",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="logging",
            enabled=True,
        )
        from audits.services import _gather_simple_rules
        rules = _gather_simple_rules(self.device)
        rule_ids = {r["id"] for r in rules}
        self.assertEqual(rule_ids, {device_rule.id, group_rule.id, global_rule.id})

    def test_gather_custom_rules_from_group(self):
        """A custom rule scoped to a group should apply to devices in that group."""
        group_rule = CustomRule.objects.create(
            name="Group Custom",
            filename="test_group.py",
            content="def test_x(): pass",
            group=self.group,
            enabled=True,
        )
        from audits.services import _gather_custom_rules
        rules = _gather_custom_rules(self.device)
        rule_ids = [r["id"] for r in rules]
        self.assertIn(group_rule.id, rule_ids)

    def test_gather_rules_disabled_group_rule_excluded(self):
        """Disabled group rules should not be gathered."""
        SimpleRule.objects.create(
            name="Disabled Group Rule",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="ntp",
            group=self.group,
            enabled=False,
        )
        from audits.services import _gather_simple_rules
        rules = _gather_simple_rules(self.device)
        self.assertEqual(len(rules), 0)
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest audits/tests.py -k "GroupScoped" -v`
Expected: FAIL — `_gather_simple_rules` doesn't exist

**Step 3: Refactor rule gathering into helper functions and expand queries**

In `backend/audits/services.py`, extract and expand the rule gathering:

Replace the inline rule queries (lines 76-88) with calls to new helper functions:

```python
def _gather_simple_rules(device):
    """
    Collect all enabled simple rules that apply to a device.

    Includes rules scoped to the device directly, any of the device's
    groups, or global rules (device and group both null).
    """
    device_groups = device.groups.all()
    return list(
        SimpleRule.objects.filter(
            Q(device=device) | Q(group__in=device_groups) | Q(device__isnull=True, group__isnull=True),
            enabled=True,
        ).values("id", "name", "rule_type", "pattern", "severity")
    )


def _gather_custom_rules(device):
    """
    Collect all enabled custom rules that apply to a device.

    Includes rules scoped to the device directly, any of the device's
    groups, or global rules (device and group both null).
    """
    device_groups = device.groups.all()
    return list(
        CustomRule.objects.filter(
            Q(device=device) | Q(group__in=device_groups) | Q(device__isnull=True, group__isnull=True),
            enabled=True,
        ).values("id", "filename", "content", "name", "severity")
    )
```

Update `run_audit` to use these:

```python
simple_rules = _gather_simple_rules(device)
custom_rules = _gather_custom_rules(device)
```

Also update `_match_custom_rule` to handle group-scoped rules:

```python
def _match_custom_rule(node_id, device):
    match = re.search(r"custom/([^:]+)", node_id)
    if not match:
        return None
    filename = match.group(1)
    device_groups = device.groups.all()
    try:
        return CustomRule.objects.get(
            Q(device=device) | Q(group__in=device_groups) | Q(device__isnull=True, group__isnull=True),
            filename=filename,
            enabled=True,
        )
    except (CustomRule.DoesNotExist, CustomRule.MultipleObjectsReturned):
        return None
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest audits/tests.py -v`
Expected: All PASS

**Step 5: Run full test suite to verify nothing is broken**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add backend/audits/services.py backend/audits/tests.py
git commit -m "feat: expand audit rule gathering to include group-scoped rules"
```

---

### Task 5: Group Bulk Audit Endpoint

**Files:**
- Modify: `backend/devices/views.py`
- Test: `backend/devices/tests.py`

**Step 1: Write failing tests for group bulk audit**

Add to `backend/devices/tests.py`:

```python
from unittest.mock import patch


class DeviceGroupRunAuditAPITests(APITestCase):
    """Tests for the run_audit action on DeviceGroupViewSet."""

    def setUp(self):
        self.group = DeviceGroup.objects.create(name="Edge Routers")
        self.device1 = Device.objects.create(
            name="r1", hostname="r1.local", api_endpoint="https://r1.local/api", enabled=True,
        )
        self.device2 = Device.objects.create(
            name="r2", hostname="r2.local", api_endpoint="https://r2.local/api", enabled=True,
        )
        self.disabled_device = Device.objects.create(
            name="r3", hostname="r3.local", api_endpoint="https://r3.local/api", enabled=False,
        )
        self.group.devices.add(self.device1, self.device2, self.disabled_device)

    @patch("audits.tasks.enqueue_audit")
    def test_run_audit_enqueues_for_enabled_devices(self, mock_enqueue):
        url = reverse("devicegroup-run-audit", kwargs={"pk": self.group.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Only enabled devices should be audited
        self.assertEqual(mock_enqueue.call_count, 2)
        called_ids = {call.args[0] for call in mock_enqueue.call_args_list}
        self.assertEqual(called_ids, {self.device1.id, self.device2.id})

    @patch("audits.tasks.enqueue_audit")
    def test_run_audit_returns_device_count(self, mock_enqueue):
        url = reverse("devicegroup-run-audit", kwargs={"pk": self.group.pk})
        response = self.client.post(url)
        self.assertEqual(response.data["audits_started"], 2)

    @patch("audits.tasks.enqueue_audit")
    def test_run_audit_empty_group(self, mock_enqueue):
        empty_group = DeviceGroup.objects.create(name="Empty")
        url = reverse("devicegroup-run-audit", kwargs={"pk": empty_group.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["audits_started"], 0)
        mock_enqueue.assert_not_called()

    def test_run_audit_not_found(self):
        url = reverse("devicegroup-run-audit", kwargs={"pk": 99999})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest devices/tests.py -k "DeviceGroupRunAudit" -v`
Expected: FAIL — `devicegroup-run-audit` URL not found

**Step 3: Implement run_audit action on DeviceGroupViewSet**

In `backend/devices/views.py`, add action to `DeviceGroupViewSet`:

```python
from audits.tasks import enqueue_audit


class DeviceGroupViewSet(viewsets.ModelViewSet):
    queryset = DeviceGroup.objects.prefetch_related("devices").all()
    serializer_class = DeviceGroupSerializer
    search_fields = ["name", "description"]

    @action(detail=True, methods=["post"])
    def run_audit(self, request, pk=None):
        group = self.get_object()
        devices = group.devices.filter(enabled=True)
        for device in devices:
            enqueue_audit(device.id, trigger="manual")
        return Response({
            "audits_started": devices.count(),
            "group": group.name,
        })
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest devices/tests.py -k "DeviceGroupRunAudit" -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add backend/devices/views.py backend/devices/tests.py
git commit -m "feat: add bulk run_audit action on DeviceGroupViewSet"
```

---

### Task 6: Admin Registration for DeviceGroup

**Files:**
- Modify: `backend/devices/admin.py`

**Step 1: Register DeviceGroup in admin**

In `backend/devices/admin.py`:

```python
from .models import Device, DeviceGroup, DeviceHeader


@admin.register(DeviceGroup)
class DeviceGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "description", "created_at"]
    search_fields = ["name", "description"]
```

**Step 2: Verify no errors**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py check`
Expected: System check identified no issues.

**Step 3: Commit**

```bash
git add backend/devices/admin.py
git commit -m "feat: register DeviceGroup in Django admin"
```

---

### Task 7: Frontend — Group CRUD Pages

**Files:**
- Create: `backend/devices/templates/devices/group_list.html`
- Create: `backend/devices/templates/devices/group_form.html`
- Create: `backend/devices/templates/devices/group_detail.html`
- Create: `backend/devices/forms.py` (add DeviceGroupForm)
- Create: `backend/devices/views_html.py` (add group views)
- Modify: `backend/devices/urls_html.py`
- Modify: `backend/templates/partials/sidebar.html`
- Modify: `backend/config/urls.py`

**Step 1: Create DeviceGroupForm**

In `backend/devices/forms.py`, add:

```python
from .models import Device, DeviceGroup, DeviceHeader


class DeviceGroupForm(forms.ModelForm):
    devices = forms.ModelMultipleChoiceField(
        queryset=Device.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = DeviceGroup
        fields = ["name", "description", "devices"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["devices"].initial = self.instance.devices.all()

    def save(self, commit=True):
        group = super().save(commit=commit)
        if commit:
            group.devices.set(self.cleaned_data["devices"])
        return group
```

Also add `groups` field to `DeviceForm`:

```python
class DeviceForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=DeviceGroup.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Device
        fields = ["name", "hostname", "api_endpoint", "enabled", "groups"]

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

**Step 2: Create group HTML views**

In `backend/devices/views_html.py`, add:

```python
from .forms import DeviceForm, DeviceGroupForm, DeviceHeaderFormSet
from .models import Device, DeviceGroup


class DeviceGroupListView(generic.ListView):
    model = DeviceGroup
    template_name = "devices/group_list.html"
    context_object_name = "groups"

    def get_queryset(self):
        return DeviceGroup.objects.prefetch_related("devices").all()


class DeviceGroupCreateView(generic.CreateView):
    model = DeviceGroup
    form_class = DeviceGroupForm
    template_name = "devices/group_form.html"

    def form_valid(self, form):
        group = form.save()
        messages.success(self.request, f'Group "{group.name}" created.')
        return redirect("group-list-html")


class DeviceGroupUpdateView(generic.UpdateView):
    model = DeviceGroup
    form_class = DeviceGroupForm
    template_name = "devices/group_form.html"

    def form_valid(self, form):
        group = form.save()
        messages.success(self.request, f'Group "{group.name}" updated.')
        return redirect("group-list-html")


class DeviceGroupDetailView(generic.DetailView):
    model = DeviceGroup
    template_name = "devices/group_detail.html"
    context_object_name = "group"

    def get_queryset(self):
        return DeviceGroup.objects.prefetch_related("devices")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        group = self.object
        ctx["devices"] = group.devices.all()
        ctx["simple_rules"] = group.simple_rules.all()
        ctx["custom_rules"] = group.custom_rules.all()
        return ctx


@require_POST
def group_delete(request, pk):
    group = get_object_or_404(DeviceGroup, pk=pk)
    name = group.name
    group.delete()
    messages.success(request, f'Group "{name}" deleted.')
    return redirect("group-list-html")


@require_POST
def group_run_audit(request, pk):
    group = get_object_or_404(DeviceGroup, pk=pk)
    devices = group.devices.filter(enabled=True)
    count = 0
    for device in devices:
        enqueue_audit(device.id, trigger="manual")
        count += 1
    html = render_to_string(
        "devices/partials/audit_started.html",
        {"device": None, "group": group, "count": count},
    )
    return HttpResponse(html)
```

**Step 3: Add group URL routes**

In `backend/devices/urls_html.py`, add:

```python
# Group routes
path("groups/", views_html.DeviceGroupListView.as_view(), name="group-list-html"),
path("groups/new/", views_html.DeviceGroupCreateView.as_view(), name="group-create-html"),
path("groups/<int:pk>/", views_html.DeviceGroupDetailView.as_view(), name="group-detail-html"),
path("groups/<int:pk>/edit/", views_html.DeviceGroupUpdateView.as_view(), name="group-update-html"),
path("groups/<int:pk>/delete/", views_html.group_delete, name="group-delete-html"),
path("groups/<int:pk>/run-audit/", views_html.group_run_audit, name="group-run-audit-html"),
```

In `backend/config/urls.py`, add:

```python
path("groups/", include("devices.urls_html")),  # WRONG — this conflicts
```

Actually, since group routes are prefixed in `urls_html.py`, add to `config/urls.py`:

```python
path("", include("devices.urls_html_groups")),
```

Or better: put group routes under the existing devices URL include by moving group paths to a prefix that doesn't conflict. Since `/devices/` is already taken, use `/groups/` directly.

Best approach: create a separate `backend/devices/urls_html_groups.py`:

```python
from django.urls import path
from . import views_html

urlpatterns = [
    path("", views_html.DeviceGroupListView.as_view(), name="group-list-html"),
    path("new/", views_html.DeviceGroupCreateView.as_view(), name="group-create-html"),
    path("<int:pk>/", views_html.DeviceGroupDetailView.as_view(), name="group-detail-html"),
    path("<int:pk>/edit/", views_html.DeviceGroupUpdateView.as_view(), name="group-update-html"),
    path("<int:pk>/delete/", views_html.group_delete, name="group-delete-html"),
    path("<int:pk>/run-audit/", views_html.group_run_audit, name="group-run-audit-html"),
]
```

In `backend/config/urls.py`, add:

```python
path("groups/", include("devices.urls_html_groups")),
```

**Step 4: Create group_list.html template**

```html
{% extends "base.html" %}

{% block title %}Groups — Netaudit{% endblock %}

{% block content %}
<div class="page-header">
    <h2>Groups</h2>
    <a href="{% url 'group-create-html' %}" class="btn btn-primary">Add Group</a>
</div>

{% if groups %}
<table class="data-table">
    <thead>
        <tr>
            <th>Name</th>
            <th>Description</th>
            <th>Devices</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        {% for group in groups %}
        <tr>
            <td><a href="{% url 'group-detail-html' group.pk %}">{{ group.name }}</a></td>
            <td>{{ group.description|truncatewords:10 }}</td>
            <td>{{ group.devices.count }}</td>
            <td>
                <div class="btn-group">
                    <a href="{% url 'group-update-html' group.pk %}" class="btn btn-secondary btn-sm">Edit</a>
                    <button class="btn btn-danger btn-sm"
                            hx-post="{% url 'group-delete-html' group.pk %}"
                            hx-confirm="Are you sure you want to delete &quot;{{ group.name }}&quot;?">
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
    <p>No groups configured yet.</p>
    <a href="{% url 'group-create-html' %}" class="btn btn-primary">Add your first group</a>
</div>
{% endif %}
{% endblock %}
```

**Step 5: Create group_form.html template**

```html
{% extends "base.html" %}

{% block title %}{% if object %}Edit Group — {{ object.name }}{% else %}Add Group{% endif %} — Netaudit{% endblock %}

{% block content %}
<div class="page-header">
    <h2>{% if object %}Edit Group{% else %}Add Group{% endif %}</h2>
</div>

<div class="card">
    <form method="post">
        {% csrf_token %}

        <div class="form-group">
            <label for="{{ form.name.id_for_label }}">Name</label>
            {{ form.name }}
            {% if form.name.errors %}<div class="form-errors">{{ form.name.errors }}</div>{% endif %}
        </div>

        <div class="form-group">
            <label for="{{ form.description.id_for_label }}">Description</label>
            {{ form.description }}
            {% if form.description.errors %}<div class="form-errors">{{ form.description.errors }}</div>{% endif %}
        </div>

        <div class="form-group">
            <label>Devices</label>
            {{ form.devices }}
            {% if form.devices.errors %}<div class="form-errors">{{ form.devices.errors }}</div>{% endif %}
        </div>

        <div class="actions">
            <button type="submit" class="btn btn-primary">
                {% if object %}Update Group{% else %}Create Group{% endif %}
            </button>
            <a href="{% url 'group-list-html' %}" class="btn btn-secondary">Cancel</a>
        </div>
    </form>
</div>
{% endblock %}
```

**Step 6: Create group_detail.html template**

```html
{% extends "base.html" %}
{% load badge_tags %}

{% block title %}{{ group.name }} — Netaudit{% endblock %}

{% block content %}
<div class="page-header">
    <h2>{{ group.name }}</h2>
    <div class="btn-group">
        <a href="{% url 'group-update-html' group.pk %}" class="btn btn-secondary">Edit</a>
        <button class="btn btn-danger"
                hx-post="{% url 'group-delete-html' group.pk %}"
                hx-confirm="Are you sure you want to delete &quot;{{ group.name }}&quot;?">
            Delete
        </button>
    </div>
</div>

<div class="card">
    <h3>Group Information</h3>
    <dl class="detail-grid">
        <dt>Description</dt>
        <dd>{{ group.description|default:"—" }}</dd>

        <dt>Created</dt>
        <dd>{{ group.created_at }}</dd>

        <dt>Updated</dt>
        <dd>{{ group.updated_at }}</dd>
    </dl>
</div>

<div class="card">
    <h3>Actions</h3>
    <div class="btn-group">
        <button class="btn btn-primary"
                hx-post="{% url 'group-run-audit-html' group.pk %}"
                hx-target="#audit-result"
                hx-indicator="#audit-spinner">
            Run Audit on All Devices
            <span id="audit-spinner" class="htmx-indicator spinner"></span>
        </button>
    </div>
    <div id="audit-result"></div>
</div>

<div class="card">
    <h3>Devices ({{ devices|length }})</h3>
    {% if devices %}
    <table class="data-table">
        <thead>
            <tr>
                <th>Name</th>
                <th>Hostname</th>
                <th>Enabled</th>
            </tr>
        </thead>
        <tbody>
            {% for device in devices %}
            <tr>
                <td><a href="{% url 'device-detail-html' device.pk %}">{{ device.name }}</a></td>
                <td>{{ device.hostname }}</td>
                <td>{{ device.enabled|enabled_badge }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <div class="empty-state">
        <p>No devices in this group yet.</p>
    </div>
    {% endif %}
</div>

<div class="card">
    <h3>Rules</h3>

    {% if simple_rules %}
    <h4>Simple Rules</h4>
    <table class="data-table">
        <thead>
            <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Severity</th>
                <th>Enabled</th>
            </tr>
        </thead>
        <tbody>
            {% for rule in simple_rules %}
            <tr>
                <td><a href="{% url 'simplerule-detail-html' rule.pk %}">{{ rule.name }}</a></td>
                <td>{{ rule.get_rule_type_display }}</td>
                <td>{{ rule.severity|severity_badge }}</td>
                <td>{{ rule.enabled|enabled_badge }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% endif %}

    {% if custom_rules %}
    <h4>Custom Rules</h4>
    <table class="data-table">
        <thead>
            <tr>
                <th>Name</th>
                <th>Filename</th>
                <th>Severity</th>
                <th>Enabled</th>
            </tr>
        </thead>
        <tbody>
            {% for rule in custom_rules %}
            <tr>
                <td><a href="{% url 'customrule-detail-html' rule.pk %}">{{ rule.name }}</a></td>
                <td>{{ rule.filename }}</td>
                <td>{{ rule.severity|severity_badge }}</td>
                <td>{{ rule.enabled|enabled_badge }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% endif %}

    {% if not simple_rules and not custom_rules %}
    <div class="empty-state">
        <p>No rules are scoped to this group.</p>
    </div>
    {% endif %}
</div>
{% endblock %}
```

**Step 7: Add Groups to sidebar**

In `backend/templates/partials/sidebar.html`, add after Devices:

```html
<li><a href="{% url 'group-list-html' %}" class="{% active_class request '/groups/' %}">Groups</a></li>
```

**Step 8: Update device_detail.html to show groups**

In `backend/devices/templates/devices/device_detail.html`, add a groups section after Device Information card:

```html
{% if device.groups.all %}
<div class="card">
    <h3>Groups</h3>
    <ul>
        {% for group in device.groups.all %}
        <li><a href="{% url 'group-detail-html' group.pk %}">{{ group.name }}</a></li>
        {% endfor %}
    </ul>
</div>
{% endif %}
```

**Step 9: Update device_list.html to show groups column**

Add a "Groups" column to the device list table.

**Step 10: Update device_form.html to show groups field**

Add groups checkbox section after the enabled field and before the headers card:

```html
<div class="card">
    <h3>Groups</h3>
    <div class="form-group">
        {{ form.groups }}
        {% if form.groups.errors %}
        <div class="form-errors">{{ form.groups.errors }}</div>
        {% endif %}
    </div>
</div>
```

**Step 11: Update rule form templates to show group dropdown**

In `backend/rules/templates/rules/simplerule_form.html` and `customrule_form.html`, add after the device field:

```html
<div class="form-group">
    <label for="{{ form.group.id_for_label }}">Group</label>
    {{ form.group }}
    {% if form.group.errors %}{{ form.group.errors }}{% endif %}
    {% if form.group.help_text %}<span class="helptext">{{ form.group.help_text }}</span>{% endif %}
</div>
```

**Step 12: Update audit_started partial for group context**

In `backend/devices/templates/devices/partials/audit_started.html`, handle both device and group cases.

**Step 13: Verify the app runs without errors**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py check`
Expected: System check identified no issues.

**Step 14: Run full test suite**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest -v`
Expected: All PASS

**Step 15: Commit**

```bash
git add backend/devices/forms.py backend/devices/views_html.py backend/devices/urls_html.py backend/devices/urls_html_groups.py backend/devices/admin.py
git add backend/devices/templates/ backend/rules/templates/ backend/templates/partials/sidebar.html
git add backend/config/urls.py
git commit -m "feat: add DeviceGroup frontend pages, sidebar navigation, and form integration"
```

---

### Task 8: Final Verification

**Step 1: Run full test suite**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python -m pytest -v`
Expected: All tests PASS

**Step 2: Run Django system checks**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py check`
Expected: No issues

**Step 3: Verify migrations are clean**

Run: `cd /Users/aaronroth/Documents/netaudit/backend && python manage.py makemigrations --check`
Expected: No changes detected
