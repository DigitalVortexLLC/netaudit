"""Tests for config_sources API endpoints."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from config_sources.models import NetmikoDeviceType


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
