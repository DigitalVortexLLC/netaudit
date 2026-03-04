"""Tests for config_sources.fetchers module."""

from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from config_sources.models import NetmikoDeviceType, SshConfigSource
from devices.models import Device


class FetchSshTests(TestCase):
    """Tests for _fetch_ssh and its integration via fetch_config."""

    def setUp(self):
        self.ndt = NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
        )
        self.ssh_source = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            hostname="10.0.0.1",
            port=22,
            username="admin",
            password="secret",
            timeout=30,
        )
        self.device = Device.objects.create(
            name="router1",
            hostname="192.168.1.1",
            config_source=self.ssh_source,
        )

    @patch("config_sources.fetchers.ConnectHandler")
    def test_fetch_ssh_returns_command_output(self, mock_handler_cls):
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "hostname router1\ninterface Gi0/0"
        mock_handler_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_handler_cls.return_value.__exit__ = MagicMock(return_value=False)

        from config_sources.fetchers import fetch_config

        result = fetch_config(self.device)
        self.assertEqual(result, "hostname router1\ninterface Gi0/0")

    @patch("config_sources.fetchers.ConnectHandler")
    def test_fetch_ssh_uses_correct_connect_params(self, mock_handler_cls):
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "output"
        mock_handler_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_handler_cls.return_value.__exit__ = MagicMock(return_value=False)

        from config_sources.fetchers import fetch_config

        fetch_config(self.device)

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

        from config_sources.fetchers import fetch_config

        fetch_config(self.device)

        mock_conn.send_command.assert_called_once_with("show running-config")

    @patch("config_sources.fetchers.ConnectHandler")
    def test_fetch_ssh_uses_command_override(self, mock_handler_cls):
        self.ssh_source.command_override = "show startup-config"
        self.ssh_source.save()

        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "output"
        mock_handler_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_handler_cls.return_value.__exit__ = MagicMock(return_value=False)

        from config_sources.fetchers import fetch_config

        fetch_config(self.device)

        mock_conn.send_command.assert_called_once_with("show startup-config")

    @patch("config_sources.fetchers.ConnectHandler")
    def test_fetch_ssh_passes_prompt_overrides(self, mock_handler_cls):
        self.ssh_source.prompt_overrides = {"expect_string": r"router#", "delay_factor": 2}
        self.ssh_source.save()

        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "output"
        mock_handler_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_handler_cls.return_value.__exit__ = MagicMock(return_value=False)

        from config_sources.fetchers import fetch_config

        fetch_config(self.device)

        mock_conn.send_command.assert_called_once_with(
            "show running-config",
            expect_string=r"router#",
            delay_factor=2,
        )

    @patch("config_sources.fetchers.ConnectHandler")
    def test_fetch_ssh_runs_extra_commands_from_device_type(self, mock_handler_cls):
        self.ndt.extra_commands = ["write memory", "show version"]
        self.ndt.save()

        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "output"
        mock_handler_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_handler_cls.return_value.__exit__ = MagicMock(return_value=False)

        from config_sources.fetchers import fetch_config

        result = fetch_config(self.device)
        self.assertEqual(result, "output")
        self.assertEqual(mock_conn.send_command.call_count, 3)
        calls = mock_conn.send_command.call_args_list
        self.assertEqual(calls[0].args[0], "show running-config")
        self.assertEqual(calls[1].args[0], "write memory")
        self.assertEqual(calls[2].args[0], "show version")

    @patch("config_sources.fetchers.ConnectHandler")
    def test_fetch_ssh_runs_extra_commands_from_ssh_source(self, mock_handler_cls):
        self.ndt.extra_commands = ["write memory"]
        self.ndt.save()
        self.ssh_source.extra_commands = ["copy running-config startup-config"]
        self.ssh_source.save()

        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "output"
        mock_handler_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_handler_cls.return_value.__exit__ = MagicMock(return_value=False)

        from config_sources.fetchers import fetch_config

        fetch_config(self.device)
        # SSH source extra_commands override device type extra_commands
        self.assertEqual(mock_conn.send_command.call_count, 2)
        calls = mock_conn.send_command.call_args_list
        self.assertEqual(calls[0].args[0], "show running-config")
        self.assertEqual(calls[1].args[0], "copy running-config startup-config")

    @patch("config_sources.fetchers.ConnectHandler")
    def test_fetch_ssh_no_extra_commands_by_default(self, mock_handler_cls):
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "output"
        mock_handler_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_handler_cls.return_value.__exit__ = MagicMock(return_value=False)

        from config_sources.fetchers import fetch_config

        fetch_config(self.device)
        mock_conn.send_command.assert_called_once_with("show running-config")

    @patch("config_sources.fetchers.ConnectHandler")
    def test_fetch_ssh_falls_back_to_device_hostname(self, mock_handler_cls):
        self.ssh_source.hostname = ""
        self.ssh_source.save()

        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "output"
        mock_handler_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_handler_cls.return_value.__exit__ = MagicMock(return_value=False)

        from config_sources.fetchers import fetch_config

        fetch_config(self.device)

        call_kwargs = mock_handler_cls.call_args[1]
        self.assertEqual(call_kwargs["host"], "192.168.1.1")


class FetchConfigDispatchTests(TestCase):
    """Tests for the fetch_config dispatch function."""

    def setUp(self):
        self.ndt = NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
        )

    def test_fetch_config_no_source_raises(self):
        device = Device.objects.create(
            name="no-source",
            hostname="10.0.0.1",
        )

        from config_sources.fetchers import fetch_config

        with self.assertRaises(ValueError) as ctx:
            fetch_config(device)
        self.assertIn("no config source configured", str(ctx.exception))

    @patch("config_sources.fetchers.ConnectHandler")
    def test_fetch_config_dispatches_ssh(self, mock_handler_cls):
        ssh_source = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            hostname="10.0.0.1",
            username="admin",
        )
        device = Device.objects.create(
            name="router1",
            hostname="192.168.1.1",
            config_source=ssh_source,
        )

        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "config output"
        mock_handler_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_handler_cls.return_value.__exit__ = MagicMock(return_value=False)

        from config_sources.fetchers import fetch_config

        result = fetch_config(device)
        self.assertEqual(result, "config output")
        mock_handler_cls.assert_called_once()

    @patch("config_sources.fetchers.ConnectHandler")
    def test_fetch_config_updates_device_fields(self, mock_handler_cls):
        ssh_source = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            hostname="10.0.0.1",
            username="admin",
        )
        device = Device.objects.create(
            name="router1",
            hostname="192.168.1.1",
            config_source=ssh_source,
        )

        mock_conn = MagicMock()
        mock_conn.send_command.return_value = "fetched config"
        mock_handler_cls.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_handler_cls.return_value.__exit__ = MagicMock(return_value=False)

        from config_sources.fetchers import fetch_config

        before = timezone.now()
        fetch_config(device)

        device.refresh_from_db()
        self.assertEqual(device.last_fetched_config, "fetched config")
        self.assertIsNotNone(device.config_fetched_at)
        self.assertGreaterEqual(device.config_fetched_at, before)
