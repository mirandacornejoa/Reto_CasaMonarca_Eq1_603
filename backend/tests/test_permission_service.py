from app.services.permission_service import PermissionService


class DummyPermission:
    def __init__(self, code):
        self.code = code


class DummyRole:
    def __init__(self, permissions):
        self.permissions = permissions


class DummyLevel:
    def __init__(self, code):
        self.code = code


class DummyUser:
    def __init__(self, level_code, is_active, permissions):
        self.access_level = DummyLevel(level_code)
        self.is_active = is_active
        self.role = DummyRole([DummyPermission(p) for p in permissions])


def test_admin_has_all_permissions():
    user = DummyUser(level_code=1, is_active=True, permissions=[])
    assert PermissionService.has_permission(user, "any.permission")


def test_non_admin_permission_validation():
    user = DummyUser(level_code=3, is_active=True, permissions=["scope.consult", "scope.edit"])
    assert PermissionService.has_permission(user, "scope.edit")
    assert not PermissionService.has_permission(user, "scope.authorize")
