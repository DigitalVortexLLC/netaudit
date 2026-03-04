"""
Tests for config_sources models.

Covers:
- NetmikoDeviceType CRUD and constraints
- ConfigSource base model
- SshConfigSource child model with encrypted fields
- Device <-> ConfigSource integration
"""

from django.db import IntegrityError, models
from django.test import TestCase

from config_sources.models import ConfigSource, NetmikoDeviceType, SshConfigSource
from devices.models import Device


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

    def test_extra_commands_default_empty_list(self):
        dt = NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
        )
        self.assertEqual(dt.extra_commands, [])

    def test_extra_commands_stored(self):
        cmds = ["write memory", "show version"]
        dt = NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
            extra_commands=cmds,
        )
        dt.refresh_from_db()
        self.assertEqual(dt.extra_commands, cmds)

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


# ──────────────────────────────────────────────────────────────────────
# ConfigSource tests
# ──────────────────────────────────────────────────────────────────────


class ConfigSourceTests(TestCase):
    def test_create_config_source_directly(self):
        cs = ConfigSource.objects.create(source_type="ssh")
        self.assertEqual(cs.source_type, "ssh")
        self.assertIsNotNone(cs.pk)
        self.assertIsNotNone(cs.created_at)
        self.assertIsNotNone(cs.updated_at)

    def test_source_type_choices(self):
        choices = dict(ConfigSource.SOURCE_TYPES)
        self.assertIn("api", choices)
        self.assertIn("git", choices)
        self.assertIn("manual", choices)
        self.assertIn("ssh", choices)
        self.assertEqual(choices["api"], "API Endpoint")
        self.assertEqual(choices["git"], "Git Repository")
        self.assertEqual(choices["manual"], "Manual")
        self.assertEqual(choices["ssh"], "SSH (Netmiko)")

    def test_str_representation(self):
        cs = ConfigSource.objects.create(source_type="api")
        self.assertEqual(str(cs), f"ConfigSource(api, pk={cs.pk})")


# ──────────────────────────────────────────────────────────────────────
# SshConfigSource tests
# ──────────────────────────────────────────────────────────────────────


class SshConfigSourceTests(TestCase):
    def setUp(self):
        self.device_type = NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
        )

    def test_create_ssh_source(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.device_type,
            hostname="192.168.1.1",
            username="admin",
            password="secret123",
        )
        self.assertEqual(ssh.source_type, "ssh")
        self.assertEqual(ssh.hostname, "192.168.1.1")
        self.assertEqual(ssh.username, "admin")
        self.assertEqual(ssh.password, "secret123")
        self.assertEqual(ssh.netmiko_device_type, self.device_type)
        self.assertIsNotNone(ssh.pk)

    def test_ssh_source_inherits_from_config_source(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.device_type,
            username="admin",
        )
        self.assertIsInstance(ssh, ConfigSource)
        # The parent ConfigSource record should also exist
        cs = ConfigSource.objects.get(pk=ssh.pk)
        self.assertEqual(cs.source_type, "ssh")

    def test_ssh_key_blank_by_default(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.device_type,
            username="admin",
        )
        self.assertEqual(ssh.ssh_key, "")

    def test_command_override_blank_by_default(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.device_type,
            username="admin",
        )
        self.assertEqual(ssh.command_override, "")

    def test_extra_commands_default_empty_list(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.device_type,
            username="admin",
        )
        self.assertEqual(ssh.extra_commands, [])

    def test_extra_commands_stored(self):
        cmds = ["write memory", "copy running-config startup-config"]
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.device_type,
            username="admin",
            extra_commands=cmds,
        )
        ssh.refresh_from_db()
        self.assertEqual(ssh.extra_commands, cmds)

    def test_prompt_overrides_default_empty_dict(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.device_type,
            username="admin",
        )
        self.assertEqual(ssh.prompt_overrides, {})

    def test_prompt_overrides_stored(self):
        overrides = {"expect_string": r"router#", "delay_factor": 2}
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.device_type,
            username="admin",
            prompt_overrides=overrides,
        )
        ssh.refresh_from_db()
        self.assertEqual(ssh.prompt_overrides, overrides)

    def test_hostname_blank_by_default(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.device_type,
            username="admin",
        )
        self.assertEqual(ssh.hostname, "")

    def test_default_port_is_22(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.device_type,
            username="admin",
        )
        self.assertEqual(ssh.port, 22)

    def test_delete_netmiko_device_type_blocked(self):
        SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.device_type,
            username="admin",
        )
        with self.assertRaises(models.ProtectedError):
            self.device_type.delete()

    def test_password_field_is_encrypted(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.device_type,
            username="admin",
            password="my_secret_password",
        )
        ssh.refresh_from_db()
        self.assertEqual(ssh.password, "my_secret_password")

    def test_str_with_hostname(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.device_type,
            hostname="10.0.0.1",
            username="admin",
        )
        self.assertEqual(str(ssh), "SSH: admin@10.0.0.1 via cisco_ios")

    def test_str_without_hostname(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.device_type,
            username="admin",
        )
        self.assertEqual(str(ssh), "SSH: admin@(device hostname) via cisco_ios")


# ──────────────────────────────────────────────────────────────────────
# Device ↔ ConfigSource integration tests
# ──────────────────────────────────────────────────────────────────────


class DeviceConfigSourceTests(TestCase):
    def setUp(self):
        self.device_type = NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
        )

    def test_device_config_source_nullable(self):
        device = Device.objects.create(
            name="router1",
            hostname="192.168.1.1",
        )
        self.assertIsNone(device.config_source)

    def test_device_can_link_to_ssh_source(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.device_type,
            hostname="192.168.1.1",
            username="admin",
        )
        device = Device.objects.create(
            name="router1",
            hostname="192.168.1.1",
            config_source=ssh,
        )
        device.refresh_from_db()
        self.assertEqual(device.config_source_id, ssh.pk)

    def test_last_fetched_config_blank_by_default(self):
        device = Device.objects.create(
            name="router1",
            hostname="192.168.1.1",
        )
        self.assertEqual(device.last_fetched_config, "")

    def test_config_fetched_at_null_by_default(self):
        device = Device.objects.create(
            name="router1",
            hostname="192.168.1.1",
        )
        self.assertIsNone(device.config_fetched_at)

    def test_delete_config_source_sets_null(self):
        ssh = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.device_type,
            hostname="192.168.1.1",
            username="admin",
        )
        device = Device.objects.create(
            name="router1",
            hostname="192.168.1.1",
            config_source=ssh,
        )
        # Delete the config source (must delete child first, then parent)
        ssh.delete()
        device.refresh_from_db()
        self.assertIsNone(device.config_source)
