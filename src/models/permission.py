from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"

class Permission(str, Enum):
    LOGS_READ = "logs:read"
    LOGS_WRITE = "logs:write"
    TRACES_READ = "traces:read"
    ALERTS_READ = "alerts:read"
    ALERTS_ACKNOWLEDGE = "alerts:acknowledge"
    RULES_READ = "rules:read"
    RULES_CREATE = "rules:create"
    RULES_UPDATE = "rules:update"
    RULES_DELETE = "rules:delete"

ROLE_PERMISSIONS: dict[str, list[str]] = {
    Role.ADMIN: [p.value for p in Permission],
    Role.USER: [
        Permission.LOGS_READ,
        Permission.LOGS_WRITE,
        Permission.TRACES_READ,
        Permission.ALERTS_READ,
        Permission.ALERTS_ACKNOWLEDGE,
        Permission.RULES_READ,
    ],
    Role.VIEWER: [
        Permission.LOGS_READ,
        Permission.TRACES_READ,
        Permission.ALERTS_READ,
    ],
}
