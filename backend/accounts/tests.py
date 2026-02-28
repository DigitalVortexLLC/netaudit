from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

User = get_user_model()


class UserModelTests(TestCase):
    def test_create_user_defaults_to_viewer(self):
        user = User.objects.create_user(
            username="viewer1", email="viewer1@test.com", password="testpass123"
        )
        self.assertEqual(user.role, "viewer")
        self.assertTrue(user.is_api_enabled)

    def test_create_user_with_admin_role(self):
        user = User.objects.create_user(
            username="admin1", email="admin1@test.com", password="testpass123",
            role="admin",
        )
        self.assertEqual(user.role, "admin")

    def test_create_user_with_editor_role(self):
        user = User.objects.create_user(
            username="editor1", email="editor1@test.com", password="testpass123",
            role="editor",
        )
        self.assertEqual(user.role, "editor")

    def test_user_str(self):
        user = User.objects.create_user(
            username="testuser", email="test@test.com", password="testpass123"
        )
        self.assertEqual(str(user), "testuser")

    def test_invalid_role_rejected(self):
        user = User(username="bad", email="bad@test.com", role="superadmin")
        with self.assertRaises(Exception):
            user.full_clean()

    def test_created_at_set_on_create(self):
        user = User.objects.create_user(
            username="ts1", email="ts1@test.com", password="testpass123"
        )
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)


class RoleGroupSyncTests(TestCase):
    def test_saving_user_creates_group_and_adds_membership(self):
        user = User.objects.create_user(
            username="g1", email="g1@test.com", password="testpass123",
            role="editor",
        )
        self.assertTrue(Group.objects.filter(name="editor").exists())
        self.assertTrue(user.groups.filter(name="editor").exists())

    def test_changing_role_updates_group(self):
        user = User.objects.create_user(
            username="g2", email="g2@test.com", password="testpass123",
            role="viewer",
        )
        self.assertTrue(user.groups.filter(name="viewer").exists())
        user.role = "admin"
        user.save()
        user.refresh_from_db()
        self.assertTrue(user.groups.filter(name="admin").exists())
        self.assertFalse(user.groups.filter(name="viewer").exists())

    def test_role_group_has_no_extra_groups(self):
        user = User.objects.create_user(
            username="g3", email="g3@test.com", password="testpass123",
            role="admin",
        )
        role_groups = {"admin", "editor", "viewer"}
        user_groups = set(user.groups.values_list("name", flat=True))
        # User should only be in their role group (among role groups)
        self.assertEqual(user_groups & role_groups, {"admin"})
