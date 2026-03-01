from unittest.mock import Mock, patch

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Device, DeviceGroup, DeviceHeader


class DeviceModelTests(TestCase):
    """Tests for the Device model."""

    def test_create_device(self):
        device = Device.objects.create(
            name="switch-01",
            hostname="switch-01.lab.local",
            api_endpoint="https://switch-01.lab.local/api",
        )
        self.assertEqual(device.name, "switch-01")
        self.assertEqual(device.hostname, "switch-01.lab.local")
        self.assertEqual(device.api_endpoint, "https://switch-01.lab.local/api")
        self.assertTrue(device.enabled)
        self.assertIsNotNone(device.created_at)
        self.assertIsNotNone(device.updated_at)

    def test_device_enabled_defaults_to_true(self):
        device = Device.objects.create(
            name="switch-02",
            hostname="switch-02.lab.local",
            api_endpoint="https://switch-02.lab.local/api",
        )
        self.assertTrue(device.enabled)

    def test_device_str(self):
        device = Device.objects.create(
            name="core-router",
            hostname="core-router.lab.local",
            api_endpoint="https://core-router.lab.local/api",
        )
        self.assertEqual(str(device), "core-router")

    def test_device_unique_name_constraint(self):
        Device.objects.create(
            name="unique-device",
            hostname="host1.local",
            api_endpoint="https://host1.local/api",
        )
        with self.assertRaises(IntegrityError):
            Device.objects.create(
                name="unique-device",
                hostname="host2.local",
                api_endpoint="https://host2.local/api",
            )

    def test_device_ordering(self):
        Device.objects.create(
            name="zebra",
            hostname="z.local",
            api_endpoint="https://z.local/api",
        )
        Device.objects.create(
            name="alpha",
            hostname="a.local",
            api_endpoint="https://a.local/api",
        )
        devices = list(Device.objects.values_list("name", flat=True))
        self.assertEqual(devices, ["alpha", "zebra"])

    def test_create_device_without_api_endpoint(self):
        device = Device.objects.create(
            name="no-endpoint",
            hostname="no-endpoint.local",
        )
        self.assertEqual(device.api_endpoint, "")

    def test_effective_api_endpoint_uses_own_endpoint(self):
        device = Device.objects.create(
            name="custom-ep",
            hostname="custom.local",
            api_endpoint="https://custom.local/api",
        )
        self.assertEqual(device.effective_api_endpoint, "https://custom.local/api")

    def test_effective_api_endpoint_uses_default_when_blank(self):
        from settings.models import SiteSettings
        site = SiteSettings.load()
        site.default_api_endpoint = "https://default.example.com/api"
        site.save()

        device = Device.objects.create(
            name="switch-99",
            hostname="switch-99.local",
        )
        self.assertEqual(
            device.effective_api_endpoint,
            "https://default.example.com/api/switch-99",
        )

    def test_effective_api_endpoint_strips_trailing_slash(self):
        from settings.models import SiteSettings
        site = SiteSettings.load()
        site.default_api_endpoint = "https://default.example.com/api/"
        site.save()

        device = Device.objects.create(
            name="switch-100",
            hostname="switch-100.local",
        )
        self.assertEqual(
            device.effective_api_endpoint,
            "https://default.example.com/api/switch-100",
        )

    def test_effective_api_endpoint_empty_when_no_config(self):
        device = Device.objects.create(
            name="orphan",
            hostname="orphan.local",
        )
        self.assertEqual(device.effective_api_endpoint, "")


class DeviceHeaderModelTests(TestCase):
    """Tests for the DeviceHeader model."""

    def setUp(self):
        self.device = Device.objects.create(
            name="header-device",
            hostname="header.local",
            api_endpoint="https://header.local/api",
        )

    def test_create_device_header(self):
        header = DeviceHeader.objects.create(
            device=self.device,
            key="Authorization",
            value="Bearer token123",
        )
        self.assertEqual(header.device, self.device)
        self.assertEqual(header.key, "Authorization")
        self.assertEqual(header.value, "Bearer token123")

    def test_device_header_str(self):
        header = DeviceHeader.objects.create(
            device=self.device,
            key="Content-Type",
            value="application/json",
        )
        self.assertEqual(str(header), "Content-Type: application/json")

    def test_device_header_unique_together(self):
        DeviceHeader.objects.create(
            device=self.device,
            key="X-Custom",
            value="value1",
        )
        with self.assertRaises(IntegrityError):
            DeviceHeader.objects.create(
                device=self.device,
                key="X-Custom",
                value="value2",
            )

    def test_device_header_cascade_delete(self):
        DeviceHeader.objects.create(
            device=self.device,
            key="Authorization",
            value="Bearer abc",
        )
        self.assertEqual(DeviceHeader.objects.count(), 1)
        self.device.delete()
        self.assertEqual(DeviceHeader.objects.count(), 0)

    def test_device_header_related_name(self):
        DeviceHeader.objects.create(
            device=self.device,
            key="X-Api-Key",
            value="key123",
        )
        headers = self.device.headers.all()
        self.assertEqual(headers.count(), 1)
        self.assertEqual(headers.first().key, "X-Api-Key")


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


class DeviceAPITests(APITestCase):
    """Tests for the Device REST API endpoints."""

    def setUp(self):
        self.device = Device.objects.create(
            name="api-device",
            hostname="api.local",
            api_endpoint="https://api.local/api",
            enabled=True,
        )
        DeviceHeader.objects.create(
            device=self.device,
            key="Authorization",
            value="Bearer test-token",
        )
        self.list_url = reverse("device-list")
        self.detail_url = reverse("device-detail", kwargs={"pk": self.device.pk})

    # ------------------------------------------------------------------ #
    # GET /api/v1/devices/ — list devices
    # ------------------------------------------------------------------ #

    def test_list_devices(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "api-device")

    def test_list_devices_returns_headers(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        headers = response.data["results"][0]["headers"]
        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[0]["key"], "Authorization")
        self.assertEqual(headers[0]["value"], "Bearer test-token")

    def test_list_devices_empty(self):
        Device.objects.all().delete()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)

    # ------------------------------------------------------------------ #
    # POST /api/v1/devices/ — create device with nested headers
    # ------------------------------------------------------------------ #

    def test_create_device(self):
        data = {
            "name": "new-device",
            "hostname": "new.local",
            "api_endpoint": "https://new.local/api",
            "enabled": True,
            "headers": [
                {"key": "Authorization", "value": "Bearer new-token"},
                {"key": "Accept", "value": "application/json"},
            ],
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "new-device")
        self.assertEqual(len(response.data["headers"]), 2)

        device = Device.objects.get(name="new-device")
        self.assertEqual(device.headers.count(), 2)

    def test_create_device_without_headers(self):
        data = {
            "name": "no-headers-device",
            "hostname": "noheaders.local",
            "api_endpoint": "https://noheaders.local/api",
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "no-headers-device")
        self.assertEqual(len(response.data["headers"]), 0)

    def test_create_device_duplicate_name_fails(self):
        data = {
            "name": "api-device",
            "hostname": "duplicate.local",
            "api_endpoint": "https://duplicate.local/api",
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_device_missing_required_fields(self):
        data = {"name": "incomplete-device"}
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_device_invalid_url(self):
        data = {
            "name": "bad-url-device",
            "hostname": "bad.local",
            "api_endpoint": "not-a-url",
        }
        response = self.client.post(self.list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------ #
    # GET /api/v1/devices/{id}/ — retrieve device
    # ------------------------------------------------------------------ #

    def test_retrieve_device(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "api-device")
        self.assertEqual(response.data["hostname"], "api.local")
        self.assertEqual(response.data["api_endpoint"], "https://api.local/api")
        self.assertTrue(response.data["enabled"])
        self.assertIn("created_at", response.data)
        self.assertIn("updated_at", response.data)

    def test_retrieve_device_includes_headers(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["headers"]), 1)
        self.assertEqual(response.data["headers"][0]["key"], "Authorization")

    def test_retrieve_device_not_found(self):
        url = reverse("device-detail", kwargs={"pk": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------ #
    # PATCH /api/v1/devices/{id}/ — update device
    # ------------------------------------------------------------------ #

    def test_partial_update_device_fields(self):
        data = {"hostname": "updated.local"}
        response = self.client.patch(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["hostname"], "updated.local")
        self.device.refresh_from_db()
        self.assertEqual(self.device.hostname, "updated.local")

    def test_partial_update_device_name(self):
        data = {"name": "renamed-device"}
        response = self.client.patch(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.device.refresh_from_db()
        self.assertEqual(self.device.name, "renamed-device")

    def test_partial_update_replaces_headers(self):
        data = {
            "headers": [
                {"key": "X-New-Header", "value": "new-value"},
            ],
        }
        response = self.client.patch(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["headers"]), 1)
        self.assertEqual(response.data["headers"][0]["key"], "X-New-Header")
        # Old header should have been deleted
        self.assertEqual(self.device.headers.count(), 1)
        self.assertFalse(
            self.device.headers.filter(key="Authorization").exists()
        )

    def test_partial_update_without_headers_preserves_them(self):
        data = {"hostname": "still-has-headers.local"}
        response = self.client.patch(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Headers should remain untouched when not provided in payload
        self.assertEqual(self.device.headers.count(), 1)
        self.assertEqual(self.device.headers.first().key, "Authorization")

    def test_full_update_device(self):
        data = {
            "name": "fully-updated",
            "hostname": "full.local",
            "api_endpoint": "https://full.local/api",
            "enabled": False,
            "headers": [],
        }
        response = self.client.put(self.detail_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.device.refresh_from_db()
        self.assertEqual(self.device.name, "fully-updated")
        self.assertFalse(self.device.enabled)
        self.assertEqual(self.device.headers.count(), 0)

    # ------------------------------------------------------------------ #
    # DELETE /api/v1/devices/{id}/ — delete device
    # ------------------------------------------------------------------ #

    def test_delete_device(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Device.objects.filter(pk=self.device.pk).exists())

    def test_delete_device_removes_headers(self):
        self.assertEqual(DeviceHeader.objects.count(), 1)
        self.client.delete(self.detail_url)
        self.assertEqual(DeviceHeader.objects.count(), 0)

    def test_delete_device_not_found(self):
        url = reverse("device-detail", kwargs={"pk": 99999})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------ #
    # POST /api/v1/devices/{id}/test_connection/ — test connection
    # ------------------------------------------------------------------ #

    @patch("devices.views.requests.get")
    def test_test_connection_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"OK"
        mock_get.return_value = mock_response

        url = reverse("device-test-connection", kwargs={"pk": self.device.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["status_code"], 200)
        self.assertEqual(response.data["content_length"], 2)

        mock_get.assert_called_once_with(
            "https://api.local/api",
            headers={"Authorization": "Bearer test-token"},
            timeout=10,
        )

    @patch("devices.views.requests.get")
    def test_test_connection_non_200_still_reports_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.content = b"Forbidden"
        mock_get.return_value = mock_response

        url = reverse("device-test-connection", kwargs={"pk": self.device.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["status_code"], 403)
        self.assertEqual(response.data["content_length"], 9)

    @patch("devices.views.requests.get")
    def test_test_connection_request_exception(self, mock_get):
        import requests as req

        mock_get.side_effect = req.ConnectionError("Connection refused")

        url = reverse("device-test-connection", kwargs={"pk": self.device.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertFalse(response.data["success"])
        self.assertIn("Connection refused", response.data["error"])

    @patch("devices.views.requests.get")
    def test_test_connection_timeout(self, mock_get):
        import requests as req

        mock_get.side_effect = req.Timeout("Request timed out")

        url = reverse("device-test-connection", kwargs={"pk": self.device.pk})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertFalse(response.data["success"])
        self.assertIn("Request timed out", response.data["error"])

    @patch("devices.views.requests.get")
    def test_test_connection_sends_device_headers(self, mock_get):
        DeviceHeader.objects.create(
            device=self.device,
            key="X-Extra",
            value="extra-value",
        )
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b""
        mock_get.return_value = mock_response

        url = reverse("device-test-connection", kwargs={"pk": self.device.pk})
        self.client.post(url)

        called_headers = mock_get.call_args[1]["headers"]
        self.assertEqual(called_headers["Authorization"], "Bearer test-token")
        self.assertEqual(called_headers["X-Extra"], "extra-value")

    def test_test_connection_device_not_found(self):
        url = reverse("device-test-connection", kwargs={"pk": 99999})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


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
