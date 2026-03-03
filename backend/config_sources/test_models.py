"""
Tests for config_sources models.

Covers:
- NetmikoDeviceType CRUD and constraints
- ConfigSource base model
- SshConfigSource child model with encrypted fields
- Device ↔ ConfigSource integration
"""

from django.db import IntegrityError
from django.test import TestCase

from config_sources.models import NetmikoDeviceType


# ──────────────────────────────────────────────────────────────────────
# NetmikoDeviceType tests
# ──────────────────────────────────────────────────────────────────────


class NetmikoDeviceTypeTests(TestCase):
    def test_create_device_type(self):
        dt = NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
        )
        self.assertEqual(dt.name, "Cisco IOS")
        self.assertEqual(dt.driver, "cisco_ios")
        self.assertEqual(dt.default_command, "show running-config")
        self.assertIsNotNone(dt.created_at)
        self.assertIsNotNone(dt.updated_at)

    def test_name_is_unique(self):
        NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
        )
        with self.assertRaises(IntegrityError):
            NetmikoDeviceType.objects.create(
                name="Cisco IOS",
                driver="cisco_ios_ssh",
                default_command="show run",
            )

    def test_str_returns_name(self):
        dt = NetmikoDeviceType.objects.create(
            name="Arista EOS",
            driver="arista_eos",
            default_command="show running-config",
        )
        self.assertEqual(str(dt), "Arista EOS")

    def test_ordering_by_name(self):
        NetmikoDeviceType.objects.create(
            name="Juniper Junos",
            driver="juniper_junos",
            default_command="show configuration",
        )
        NetmikoDeviceType.objects.create(
            name="Arista EOS",
            driver="arista_eos",
            default_command="show running-config",
        )
        NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
        )
        names = list(NetmikoDeviceType.objects.values_list("name", flat=True))
        self.assertEqual(names, ["Arista EOS", "Cisco IOS", "Juniper Junos"])

    def test_description_blank_allowed(self):
        dt = NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
        )
        self.assertEqual(dt.description, "")

        dt2 = NetmikoDeviceType.objects.create(
            name="Arista EOS",
            driver="arista_eos",
            default_command="show running-config",
            description="Arista EOS switches",
        )
        self.assertEqual(dt2.description, "Arista EOS switches")
