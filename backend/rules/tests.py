from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from devices.models import Device, DeviceGroup
from rules.models import CustomRule, SimpleRule


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class SimpleRuleModelTests(TestCase):
    """Tests for the SimpleRule model."""

    def _create_simple_rule(self, **kwargs):
        defaults = {
            "name": "Check NTP",
            "description": "Ensure NTP is configured",
            "rule_type": SimpleRule.RuleType.MUST_CONTAIN,
            "pattern": "ntp server",
            "severity": SimpleRule.Severity.HIGH,
            "enabled": True,
        }
        defaults.update(kwargs)
        return SimpleRule.objects.create(**defaults)

    def test_create_must_contain(self):
        rule = self._create_simple_rule(
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
        )
        self.assertEqual(rule.rule_type, "must_contain")
        self.assertTrue(SimpleRule.objects.filter(pk=rule.pk).exists())

    def test_create_must_not_contain(self):
        rule = self._create_simple_rule(
            name="No Telnet",
            rule_type=SimpleRule.RuleType.MUST_NOT_CONTAIN,
            pattern="transport input telnet",
        )
        self.assertEqual(rule.rule_type, "must_not_contain")

    def test_create_regex_match(self):
        rule = self._create_simple_rule(
            name="Regex NTP",
            rule_type=SimpleRule.RuleType.REGEX_MATCH,
            pattern=r"ntp server \d+\.\d+\.\d+\.\d+",
        )
        self.assertEqual(rule.rule_type, "regex_match")

    def test_create_regex_no_match(self):
        rule = self._create_simple_rule(
            name="No Weak Cipher",
            rule_type=SimpleRule.RuleType.REGEX_NO_MATCH,
            pattern=r"crypto.*des",
        )
        self.assertEqual(rule.rule_type, "regex_no_match")

    def test_str_method(self):
        rule = self._create_simple_rule(
            name="Check NTP",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
        )
        self.assertEqual(str(rule), "Check NTP (Must Contain)")

    def test_str_method_regex_match(self):
        rule = self._create_simple_rule(
            name="Regex Test",
            rule_type=SimpleRule.RuleType.REGEX_MATCH,
        )
        self.assertEqual(str(rule), "Regex Test (Regex Match)")

    def test_default_severity_is_medium(self):
        rule = SimpleRule.objects.create(
            name="Default Severity",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="something",
        )
        self.assertEqual(rule.severity, SimpleRule.Severity.MEDIUM)

    def test_default_enabled_is_true(self):
        rule = SimpleRule.objects.create(
            name="Enabled Default",
            rule_type=SimpleRule.RuleType.MUST_CONTAIN,
            pattern="something",
        )
        self.assertTrue(rule.enabled)

    def test_device_fk_nullable(self):
        rule = self._create_simple_rule(device=None)
        self.assertIsNone(rule.device)

    def test_device_fk_assigned(self):
        device = Device.objects.create(
            name="router-1",
            hostname="router-1.example.com",
            api_endpoint="https://router-1.example.com/api",
        )
        rule = self._create_simple_rule(device=device)
        self.assertEqual(rule.device, device)

    def test_ordering(self):
        self._create_simple_rule(name="Zebra Rule")
        self._create_simple_rule(name="Alpha Rule")
        rules = list(SimpleRule.objects.values_list("name", flat=True))
        self.assertEqual(rules, ["Alpha Rule", "Zebra Rule"])


class CustomRuleModelTests(TestCase):
    """Tests for the CustomRule model."""

    def _create_custom_rule(self, **kwargs):
        defaults = {
            "name": "NTP Check",
            "description": "Pytest-based NTP validation",
            "filename": "test_ntp.py",
            "content": "def test_ntp():\n    assert True\n",
            "severity": CustomRule.Severity.MEDIUM,
            "enabled": True,
        }
        defaults.update(kwargs)
        return CustomRule.objects.create(**defaults)

    def test_create_custom_rule(self):
        rule = self._create_custom_rule()
        self.assertTrue(CustomRule.objects.filter(pk=rule.pk).exists())
        self.assertEqual(rule.filename, "test_ntp.py")

    def test_str_method(self):
        rule = self._create_custom_rule(name="NTP Check")
        self.assertEqual(str(rule), "NTP Check")

    def test_clean_valid_filename(self):
        rule = self._create_custom_rule(filename="test_valid.py")
        # Should not raise
        rule.full_clean()

    def test_clean_filename_missing_test_prefix(self):
        rule = self._create_custom_rule(filename="ntp_check.py")
        with self.assertRaises(ValidationError) as ctx:
            rule.full_clean()
        self.assertIn("filename", ctx.exception.message_dict)

    def test_clean_filename_missing_py_suffix(self):
        rule = self._create_custom_rule(filename="test_ntp.txt")
        with self.assertRaises(ValidationError) as ctx:
            rule.full_clean()
        self.assertIn("filename", ctx.exception.message_dict)

    def test_clean_filename_no_prefix_no_suffix(self):
        rule = self._create_custom_rule(filename="bad_name")
        with self.assertRaises(ValidationError) as ctx:
            rule.full_clean()
        self.assertIn("filename", ctx.exception.message_dict)

    def test_device_fk_nullable(self):
        rule = self._create_custom_rule(device=None)
        self.assertIsNone(rule.device)

    def test_ordering(self):
        self._create_custom_rule(name="Zebra Custom")
        self._create_custom_rule(name="Alpha Custom")
        rules = list(CustomRule.objects.values_list("name", flat=True))
        self.assertEqual(rules, ["Alpha Custom", "Zebra Custom"])


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

VALID_PYTHON = "def test_example():\n    assert True\n"
INVALID_PYTHON = "def test_example(\n    assert True\n"


class SimpleRuleAPITests(APITestCase):
    """CRUD tests for the SimpleRule API at /api/v1/rules/simple/."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="testpass123",
            role="admin",
        )
        self.client.force_authenticate(user=self.user)

        self.list_url = reverse("simplerule-list")
        self.payload = {
            "name": "Check NTP",
            "description": "Ensure NTP is configured",
            "rule_type": "must_contain",
            "pattern": "ntp server",
            "severity": "high",
            "enabled": True,
        }

    # -- List ---------------------------------------------------------------

    def test_list_empty(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    def test_list_returns_rules(self):
        SimpleRule.objects.create(**self.payload)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    # -- Create -------------------------------------------------------------

    def test_create(self):
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SimpleRule.objects.count(), 1)
        rule = SimpleRule.objects.first()
        self.assertEqual(rule.name, "Check NTP")
        self.assertEqual(rule.rule_type, "must_contain")

    def test_create_all_rule_types(self):
        for rt in SimpleRule.RuleType.values:
            payload = {**self.payload, "name": f"Rule {rt}", "rule_type": rt}
            response = self.client.post(self.list_url, payload, format="json")
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                f"Failed to create rule with rule_type={rt}",
            )

    def test_create_without_required_field(self):
        payload = {**self.payload}
        del payload["pattern"]
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- Retrieve -----------------------------------------------------------

    def test_retrieve(self):
        rule = SimpleRule.objects.create(**self.payload)
        url = reverse("simplerule-detail", args=[rule.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Check NTP")

    def test_retrieve_not_found(self):
        url = reverse("simplerule-detail", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -- Update (PUT) -------------------------------------------------------

    def test_update_put(self):
        rule = SimpleRule.objects.create(**self.payload)
        url = reverse("simplerule-detail", args=[rule.pk])
        updated = {**self.payload, "name": "Updated NTP Check"}
        response = self.client.put(url, updated, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rule.refresh_from_db()
        self.assertEqual(rule.name, "Updated NTP Check")

    # -- Partial Update (PATCH) ---------------------------------------------

    def test_update_patch(self):
        rule = SimpleRule.objects.create(**self.payload)
        url = reverse("simplerule-detail", args=[rule.pk])
        response = self.client.patch(
            url, {"severity": "critical"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rule.refresh_from_db()
        self.assertEqual(rule.severity, "critical")

    # -- Delete -------------------------------------------------------------

    def test_delete(self):
        rule = SimpleRule.objects.create(**self.payload)
        url = reverse("simplerule-detail", args=[rule.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SimpleRule.objects.filter(pk=rule.pk).exists())

    # -- With Device FK -----------------------------------------------------

    def test_create_with_device(self):
        device = Device.objects.create(
            name="router-1",
            hostname="router-1.example.com",
            api_endpoint="https://router-1.example.com/api",
        )
        payload = {**self.payload, "device": device.pk}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["device"], device.pk)


class CustomRuleAPITests(APITestCase):
    """CRUD tests for the CustomRule API at /api/v1/rules/custom/."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="testpass123",
            role="admin",
        )
        self.client.force_authenticate(user=self.user)

        self.list_url = reverse("customrule-list")
        self.payload = {
            "name": "NTP Pytest",
            "description": "Pytest NTP check",
            "filename": "test_ntp.py",
            "content": VALID_PYTHON,
            "severity": "medium",
            "enabled": True,
        }

    # -- List ---------------------------------------------------------------

    def test_list_empty(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"], [])

    def test_list_returns_rules(self):
        CustomRule.objects.create(**self.payload)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    # -- Create -------------------------------------------------------------

    def test_create(self):
        response = self.client.post(self.list_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CustomRule.objects.count(), 1)
        rule = CustomRule.objects.first()
        self.assertEqual(rule.name, "NTP Pytest")

    def test_create_invalid_filename_no_test_prefix(self):
        payload = {**self.payload, "filename": "ntp_check.py"}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("filename", response.data)

    def test_create_invalid_filename_no_py_suffix(self):
        payload = {**self.payload, "filename": "test_ntp.txt"}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("filename", response.data)

    def test_create_invalid_python_syntax(self):
        payload = {**self.payload, "content": INVALID_PYTHON}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content", response.data)

    def test_create_without_required_field(self):
        payload = {**self.payload}
        del payload["content"]
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # -- Retrieve -----------------------------------------------------------

    def test_retrieve(self):
        rule = CustomRule.objects.create(**self.payload)
        url = reverse("customrule-detail", args=[rule.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "NTP Pytest")

    def test_retrieve_not_found(self):
        url = reverse("customrule-detail", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -- Update (PUT) -------------------------------------------------------

    def test_update_put(self):
        rule = CustomRule.objects.create(**self.payload)
        url = reverse("customrule-detail", args=[rule.pk])
        updated = {**self.payload, "name": "Updated NTP Pytest"}
        response = self.client.put(url, updated, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rule.refresh_from_db()
        self.assertEqual(rule.name, "Updated NTP Pytest")

    def test_update_put_rejects_invalid_syntax(self):
        rule = CustomRule.objects.create(**self.payload)
        url = reverse("customrule-detail", args=[rule.pk])
        updated = {**self.payload, "content": INVALID_PYTHON}
        response = self.client.put(url, updated, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content", response.data)

    def test_update_put_rejects_bad_filename(self):
        rule = CustomRule.objects.create(**self.payload)
        url = reverse("customrule-detail", args=[rule.pk])
        updated = {**self.payload, "filename": "bad_name.py"}
        response = self.client.put(url, updated, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("filename", response.data)

    # -- Partial Update (PATCH) ---------------------------------------------

    def test_update_patch(self):
        rule = CustomRule.objects.create(**self.payload)
        url = reverse("customrule-detail", args=[rule.pk])
        response = self.client.patch(
            url, {"severity": "critical"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rule.refresh_from_db()
        self.assertEqual(rule.severity, "critical")

    def test_patch_rejects_invalid_syntax(self):
        rule = CustomRule.objects.create(**self.payload)
        url = reverse("customrule-detail", args=[rule.pk])
        response = self.client.patch(
            url, {"content": INVALID_PYTHON}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content", response.data)

    # -- Delete -------------------------------------------------------------

    def test_delete(self):
        rule = CustomRule.objects.create(**self.payload)
        url = reverse("customrule-detail", args=[rule.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CustomRule.objects.filter(pk=rule.pk).exists())

    # -- Validate action ----------------------------------------------------

    def test_validate_action_valid_python(self):
        rule = CustomRule.objects.create(**self.payload)
        url = reverse("customrule-validate", args=[rule.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["valid"])

    def test_validate_action_invalid_python(self):
        rule = CustomRule.objects.create(
            **{**self.payload, "content": INVALID_PYTHON}
        )
        url = reverse("customrule-validate", args=[rule.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["valid"])
        self.assertIn("error", response.data)

    def test_validate_action_not_found(self):
        url = reverse("customrule-validate", args=[99999])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -- With Device FK -----------------------------------------------------

    def test_create_with_device(self):
        device = Device.objects.create(
            name="switch-1",
            hostname="switch-1.example.com",
            api_endpoint="https://switch-1.example.com/api",
        )
        payload = {**self.payload, "device": device.pk}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["device"], device.pk)


# ---------------------------------------------------------------------------
# Group FK tests
# ---------------------------------------------------------------------------


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
