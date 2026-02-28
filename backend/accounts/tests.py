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
