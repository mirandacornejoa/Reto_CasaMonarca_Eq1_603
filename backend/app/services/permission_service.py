from app.models.user import User


class PermissionService:
    @staticmethod
    def is_admin(user: User) -> bool:
        return bool(user.access_level and user.access_level.code == 1 and user.is_active)

    @staticmethod
    def has_permission(user: User, permission_code: str) -> bool:
        if PermissionService.is_admin(user):
            return True

        if not user.role:
            return False

        role_permissions = {permission.code for permission in user.role.permissions}
        return permission_code in role_permissions
