"""Tests for config_sources API endpoints."""

from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from config_sources.models import ConfigSource, NetmikoDeviceType, SshConfigSource
from devices.models import Device


class NetmikoDeviceTypeAPITests(APITestCase):
    """Tests for the NetmikoDeviceType REST API endpoints."""

    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin",
            password="adminpass123",
            role="admin",
        )
        self.editor_user = User.objects.create_user(
            username="editor",
            password="editorpass123",
            role="editor",
        )
        self.viewer_user = User.objects.create_user(
            username="viewer",
            password="viewerpass123",
            role="viewer",
        )
        self.client.force_authenticate(user=self.admin_user)

        self.ndt = NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
            description="Cisco IOS devices",
        )
        self.list_url = reverse("netmikodevicetype-list")
        self.detail_url = reverse(
            "netmikodevicetype-detail", kwargs={"pk": self.ndt.pk}
        )

    def test_list_device_types(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Cisco IOS")
        self.assertEqual(response.data["results"][0]["driver"], "cisco_ios")

    def test_create_device_type(self):
        data = {
            "name": "Arista EOS",
            "driver": "arista_eos",
            "default_command": "show running-config",
            "description": "Arista EOS switches",
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Arista EOS")
        self.assertEqual(NetmikoDeviceType.objects.count(), 2)

    def test_retrieve_device_type(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Cisco IOS")
        self.assertEqual(response.data["driver"], "cisco_ios")
        self.assertEqual(response.data["default_command"], "show running-config")
        self.assertIn("created_at", response.data)
        self.assertIn("updated_at", response.data)

    def test_update_device_type(self):
        data = {
            "name": "Cisco IOS Updated",
            "driver": "cisco_ios",
            "default_command": "show run",
            "description": "Updated description",
        }
        response = self.client.put(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ndt.refresh_from_db()
        self.assertEqual(self.ndt.name, "Cisco IOS Updated")
        self.assertEqual(self.ndt.default_command, "show run")

    def test_delete_device_type(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(NetmikoDeviceType.objects.filter(pk=self.ndt.pk).exists())

    def test_create_device_type_with_extra_commands(self):
        data = {
            "name": "Cisco IOS XE",
            "driver": "cisco_ios",
            "default_command": "show running-config",
            "extra_commands": ["write memory", "show version"],
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["extra_commands"], ["write memory", "show version"])
        dt = NetmikoDeviceType.objects.get(name="Cisco IOS XE")
        self.assertEqual(dt.extra_commands, ["write memory", "show version"])

    def test_retrieve_device_type_includes_extra_commands(self):
        self.ndt.extra_commands = ["write memory"]
        self.ndt.save()
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["extra_commands"], ["write memory"])

    def test_update_device_type_extra_commands(self):
        data = {
            "name": "Cisco IOS",
            "driver": "cisco_ios",
            "default_command": "show running-config",
            "extra_commands": ["write memory"],
        }
        response = self.client.put(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.ndt.refresh_from_db()
        self.assertEqual(self.ndt.extra_commands, ["write memory"])

    def test_viewer_can_list(self):
        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_viewer_cannot_create(self):
        self.client.force_authenticate(user=self.viewer_user)
        data = {
            "name": "Juniper Junos",
            "driver": "juniper_junos",
            "default_command": "show configuration",
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class DeviceWithSshConfigSourceAPITests(APITestCase):
    """Tests for Device API with nested SSH config source."""

    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin",
            password="adminpass123",
            role="admin",
        )
        self.client.force_authenticate(user=self.admin_user)

        self.ndt = NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
        )
        self.list_url = reverse("device-list")

    def test_create_device_with_ssh_source(self):
        data = {
            "name": "router1",
            "hostname": "10.0.0.1",
            "config_source": {
                "source_type": "ssh",
                "netmiko_device_type": self.ndt.pk,
                "username": "admin",
                "password": "secret",
                "hostname": "10.0.0.1",
            },
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        device = Device.objects.get(name="router1")
        self.assertIsNotNone(device.config_source)
        self.assertEqual(device.config_source.source_type, "ssh")
        ssh = device.config_source.sshconfigsource
        self.assertEqual(ssh.username, "admin")
        self.assertEqual(ssh.hostname, "10.0.0.1")

    def test_create_device_without_config_source(self):
        data = {
            "name": "router2",
            "hostname": "10.0.0.2",
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        device = Device.objects.get(name="router2")
        self.assertIsNone(device.config_source)

    def test_device_response_includes_config_source(self):
        data = {
            "name": "router3",
            "hostname": "10.0.0.3",
            "config_source": {
                "source_type": "ssh",
                "netmiko_device_type": self.ndt.pk,
                "username": "admin",
                "password": "secret",
            },
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cs = response.data["config_source"]
        self.assertEqual(cs["source_type"], "ssh")
        self.assertEqual(cs["username"], "admin")
        self.assertEqual(cs["netmiko_device_type"], self.ndt.pk)
        # password should NOT be in the response
        self.assertNotIn("password", cs)

    def test_update_device_config_source(self):
        # Create device first
        data = {
            "name": "router4",
            "hostname": "10.0.0.4",
            "config_source": {
                "source_type": "ssh",
                "netmiko_device_type": self.ndt.pk,
                "username": "admin",
                "password": "secret",
            },
        }
        response = self.client.post(self.list_url, data, format="json")
        device_id = response.data["id"]
        detail_url = reverse("device-detail", kwargs={"pk": device_id})

        # Update with new config source
        update_data = {
            "config_source": {
                "source_type": "ssh",
                "netmiko_device_type": self.ndt.pk,
                "username": "newuser",
                "password": "newpass",
                "hostname": "10.0.0.99",
            },
        }
        response = self.client.patch(detail_url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["config_source"]["username"], "newuser")
        self.assertEqual(response.data["config_source"]["hostname"], "10.0.0.99")

    def test_remove_config_source_by_setting_null(self):
        # Create device with source
        data = {
            "name": "router5",
            "hostname": "10.0.0.5",
            "config_source": {
                "source_type": "ssh",
                "netmiko_device_type": self.ndt.pk,
                "username": "admin",
            },
        }
        response = self.client.post(self.list_url, data, format="json")
        device_id = response.data["id"]
        detail_url = reverse("device-detail", kwargs={"pk": device_id})

        # Remove config source
        update_data = {"config_source": None}
        response = self.client.patch(detail_url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["config_source"])

        device = Device.objects.get(pk=device_id)
        self.assertIsNone(device.config_source)

    def test_device_includes_last_fetched_config(self):
        device = Device.objects.create(
            name="router6",
            hostname="10.0.0.6",
            last_fetched_config="hostname router6\n!",
        )
        detail_url = reverse("device-detail", kwargs={"pk": device.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["last_fetched_config"], "hostname router6\n!")
        self.assertIn("config_fetched_at", response.data)

    def test_create_ssh_source_with_prompt_overrides(self):
        data = {
            "name": "router7",
            "hostname": "10.0.0.7",
            "config_source": {
                "source_type": "ssh",
                "netmiko_device_type": self.ndt.pk,
                "username": "admin",
                "prompt_overrides": {"expect_string": r"router#", "delay_factor": 2},
            },
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        device = Device.objects.get(name="router7")
        ssh = device.config_source.sshconfigsource
        self.assertEqual(ssh.prompt_overrides["expect_string"], r"router#")
        self.assertEqual(ssh.prompt_overrides["delay_factor"], 2)


    def test_create_ssh_source_with_extra_commands(self):
        data = {
            "name": "router8",
            "hostname": "10.0.0.8",
            "config_source": {
                "source_type": "ssh",
                "netmiko_device_type": self.ndt.pk,
                "username": "admin",
                "extra_commands": ["write memory"],
            },
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        device = Device.objects.get(name="router8")
        ssh = device.config_source.sshconfigsource
        self.assertEqual(ssh.extra_commands, ["write memory"])

    def test_device_response_includes_extra_commands(self):
        data = {
            "name": "router9",
            "hostname": "10.0.0.9",
            "config_source": {
                "source_type": "ssh",
                "netmiko_device_type": self.ndt.pk,
                "username": "admin",
                "extra_commands": ["write memory", "show version"],
            },
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cs = response.data["config_source"]
        self.assertEqual(cs["extra_commands"], ["write memory", "show version"])


class FetchConfigAPITests(APITestCase):
    """Tests for the fetch_config action on DeviceViewSet."""

    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin",
            password="adminpass123",
            role="admin",
        )
        self.client.force_authenticate(user=self.admin_user)

        self.ndt = NetmikoDeviceType.objects.create(
            name="Cisco IOS",
            driver="cisco_ios",
            default_command="show running-config",
        )

    @patch("devices.views.config_tasks.enqueue_fetch_config")
    def test_fetch_config_queues_task(self, mock_enqueue):
        ssh_source = SshConfigSource.objects.create(
            source_type="ssh",
            netmiko_device_type=self.ndt,
            hostname="10.0.0.1",
            username="admin",
        )
        device = Device.objects.create(
            name="router1",
            hostname="10.0.0.1",
            config_source=ssh_source,
        )
        url = reverse("device-fetch-config", kwargs={"pk": device.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data["status"], "queued")
        self.assertEqual(response.data["device_id"], device.id)
        mock_enqueue.assert_called_once_with(device.id)

    def test_fetch_config_no_source_returns_400(self):
        device = Device.objects.create(
            name="no-source",
            hostname="10.0.0.2",
        )
        url = reverse("device-fetch-config", kwargs={"pk": device.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
