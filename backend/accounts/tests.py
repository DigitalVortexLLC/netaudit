from unittest.mock import Mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase, override_settings
from rest_framework.test import APIRequestFactory, APITestCase as DRFAPITestCase

from accounts.permissions import IsAdminRole, IsEditorOrAbove, IsViewerOrAbove

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


class PermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = User.objects.create_user(
            username="padmin", email="padmin@test.com", password="testpass123",
            role="admin",
        )
        self.editor = User.objects.create_user(
            username="peditor", email="peditor@test.com", password="testpass123",
            role="editor",
        )
        self.viewer = User.objects.create_user(
            username="pviewer", email="pviewer@test.com", password="testpass123",
            role="viewer",
        )

    def _request_for(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_admin_permission(self):
        perm = IsAdminRole()
        self.assertTrue(perm.has_permission(self._request_for(self.admin), None))
        self.assertFalse(perm.has_permission(self._request_for(self.editor), None))
        self.assertFalse(perm.has_permission(self._request_for(self.viewer), None))

    def test_editor_or_above_permission(self):
        perm = IsEditorOrAbove()
        self.assertTrue(perm.has_permission(self._request_for(self.admin), None))
        self.assertTrue(perm.has_permission(self._request_for(self.editor), None))
        self.assertFalse(perm.has_permission(self._request_for(self.viewer), None))

    def test_viewer_or_above_permission(self):
        perm = IsViewerOrAbove()
        self.assertTrue(perm.has_permission(self._request_for(self.admin), None))
        self.assertTrue(perm.has_permission(self._request_for(self.editor), None))
        self.assertTrue(perm.has_permission(self._request_for(self.viewer), None))

    def test_unauthenticated_denied(self):
        request = self.factory.get("/")
        request.user = Mock(is_authenticated=False)
        self.assertFalse(IsViewerOrAbove().has_permission(request, None))


class AuthHookMiddlewareTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="mwuser", email="mw@test.com", password="testpass123",
        )

    def test_hooks_called_in_order(self):
        """Verify pre_authenticate and post_authenticate are called."""
        from accounts.middleware import AuthHookMiddleware

        call_log = []

        class TestHook:
            def pre_authenticate(self, request):
                call_log.append("pre")

            def post_authenticate(self, request):
                call_log.append("post")

            def on_response(self, request, response):
                call_log.append("response")

        def get_response(request):
            from django.http import HttpResponse
            return HttpResponse("ok")

        middleware = AuthHookMiddleware(get_response)
        middleware._hooks = [TestHook()]

        request = self.factory.get("/")
        request.user = self.user
        response = middleware(request)

        self.assertEqual(call_log, ["pre", "post", "response"])

    def test_pre_authenticate_can_short_circuit(self):
        """If pre_authenticate returns a response, skip the view."""
        from accounts.middleware import AuthHookMiddleware

        class BlockingHook:
            def pre_authenticate(self, request):
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden("blocked")

        def get_response(request):
            from django.http import HttpResponse
            return HttpResponse("ok")

        middleware = AuthHookMiddleware(get_response)
        middleware._hooks = [BlockingHook()]

        request = self.factory.get("/")
        request.user = self.user
        response = middleware(request)

        self.assertEqual(response.status_code, 403)


def _patch_context_copy():
    """Monkey-patch Django template context __copy__ for Python 3.14 compat.

    Python 3.14 changed copy.copy() semantics for objects using __slots__,
    breaking Django's BaseContext.__copy__. This is a known Django issue
    that will be fixed upstream.
    """
    import sys

    if sys.version_info < (3, 14):
        return
    from django.template.context import BaseContext

    original_copy = BaseContext.__copy__

    def _safe_copy(self):
        import copy as copy_mod

        cls = self.__class__
        result = cls.__new__(cls)
        result.dicts = self.dicts[:]
        return result

    BaseContext.__copy__ = _safe_copy


_patch_context_copy()


@override_settings(ACCOUNT_EMAIL_VERIFICATION="none")
class AuthFlowTests(TestCase):
    """End-to-end auth flow tests."""

    def test_registration_creates_viewer_by_default(self):
        """Second+ user gets viewer role via AccountAdapter."""
        # Ensure at least one user exists so the adapter doesn't assign admin
        User.objects.create_user(
            username="existing", email="existing@test.com", password="testpass123"
        )
        from rest_framework.test import APIClient

        api_client = APIClient()
        response = api_client.post(
            "/api/v1/auth/register/",
            {
                "username": "newuser",
                "email": "new@test.com",
                "password1": "complexpass123!",
                "password2": "complexpass123!",
            },
            format="json",
        )
        self.assertIn(response.status_code, (200, 201, 204))
        user = User.objects.get(username="newuser")
        self.assertEqual(user.role, "viewer")

    def test_first_user_gets_admin_role(self):
        """First user gets admin role via AccountAdapter."""
        User.objects.all().delete()
        from rest_framework.test import APIClient

        api_client = APIClient()
        response = api_client.post(
            "/api/v1/auth/register/",
            {
                "username": "firstuser",
                "email": "first@test.com",
                "password1": "complexpass123!",
                "password2": "complexpass123!",
            },
            format="json",
        )
        self.assertIn(response.status_code, (200, 201, 204))
        user = User.objects.get(username="firstuser")
        self.assertEqual(user.role, "admin")

    def test_login_grants_access_to_protected_views(self):
        """Authenticated user can access protected HTML views."""
        User.objects.create_user(
            username="flowuser",
            email="flow@test.com",
            password="testpass123",
        )
        logged_in = self.client.login(username="flowuser", password="testpass123")
        self.assertTrue(logged_in)

        # Access protected page
        response = self.client.get("/devices/")
        self.assertEqual(response.status_code, 200)

    def test_logout_blocks_access_to_protected_views(self):
        """After logout, protected views redirect to login."""
        User.objects.create_user(
            username="flowuser",
            email="flow@test.com",
            password="testpass123",
        )
        self.client.login(username="flowuser", password="testpass123")
        self.client.logout()

        # Protected page redirects to login
        response = self.client.get("/devices/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_unauthenticated_redirected_to_login(self):
        """Unauthenticated access to protected views redirects to login."""
        response = self.client.get("/devices/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_viewer_cannot_access_editor_views(self):
        """Viewer role is blocked from editor-only actions."""
        User.objects.create_user(
            username="viewer1",
            email="v@test.com",
            password="testpass123",
            role="viewer",
        )
        self.client.login(username="viewer1", password="testpass123")
        # Device create requires editor role
        response = self.client.get("/devices/new/")
        self.assertEqual(response.status_code, 403)


class JWTAuthTests(DRFAPITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="jwtuser",
            email="jwt@test.com",
            password="testpass123",
            role="editor",
        )

    def test_obtain_jwt_token(self):
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "username": "jwtuser",
                "password": "testpass123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)

    def test_access_api_with_jwt(self):
        # Get token
        response = self.client.post(
            "/api/v1/auth/login/",
            {
                "username": "jwtuser",
                "password": "testpass123",
            },
        )
        token = response.data["access"]
        # Use token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get("/api/v1/devices/")
        self.assertEqual(response.status_code, 200)

    def test_invalid_token_returns_401(self):
        self.client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token")
        response = self.client.get("/api/v1/devices/")
        self.assertEqual(response.status_code, 401)
