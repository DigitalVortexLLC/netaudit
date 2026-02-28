from rest_framework.permissions import BasePermission

ROLE_HIERARCHY = {"admin": 3, "editor": 2, "viewer": 1}


class _RolePermission(BasePermission):
    min_role = "viewer"

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        user_level = ROLE_HIERARCHY.get(request.user.role, 0)
        required_level = ROLE_HIERARCHY[self.min_role]
        return user_level >= required_level


class IsAdminRole(_RolePermission):
    min_role = "admin"


class IsEditorOrAbove(_RolePermission):
    min_role = "editor"


class IsViewerOrAbove(_RolePermission):
    min_role = "viewer"
