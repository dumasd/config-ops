import re
from enum import Enum

PROPERTIES = "properties"
YAML = "yaml"
JSON = "json"
XML = "xml"
TEXT = "text"
UNKNOWN = "unknown"

CONFIG_ENV_NAME = "CONFIGOPS_CONFIG"
CONFIG_FILE_ENV_NAME = "CONFIGOPS_CONFIG_FILE"

MYSQL = "mysql"
POSTGRESQL = "postgresql"
ORACLE = "oracle"

GREMLIN = "gremlin"
OPEN_CYPHER = "openCypher"
SPARQL = "sparql"

X_WORKSPACE = "X-Workspace"
X_WORKER = "X-Worker"

CONTROLLER_SOCKETIO = "CONFIG_OPS_CONTROLLER_SOCKETIO"
CONTROLLER_NAMESPACE = "CONFIG_OPS_CONTROLLER_NAMESPACE"
WORKER_NAMESPACE = "CONFIG_OPS_WORKER_NAMESPACE"
CLUSTER_REQUEST_ID = "CLUSTER_REQUEST_ID"


class GraphdbDialect(Enum):
    NEPTUNE = "neptune"
    NEO4J = "neo4j"
    JENAFUSEKI = "jenafuseki"
    JANUSGRAPH = "janusgraph"


class ChangelogExeType(Enum):
    INIT = "INIT"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    # RERUN = "RERUN"

    def matches(self, value):
        return self.value == value


class SystemType(Enum):
    NACOS = "NACOS"
    ELASTICSEARCH = "ELASTICSEARCH"
    DATABASE = "DATABASE"
    REDIS = "REDIS"
    GRAPHDB = "GRAPHDB"


class NodeRole(Enum):
    CONTROLLER = "controller"
    WORKER = "worker"

    def matches(self, value):
        return self.value == value


class PermissionType(Enum):
    WEB_MENU = "WEB_MENU"
    WORKSPACE = "WORKSPACE"
    WORKER = "WORKER"
    OBJECT = "OBJECT"


class PermissionModule(Enum):
    # 系统管理维度
    GROUP_MANAGE = "GROUP_MANAGE"  # 用户组管理
    WORKSPACE_MANAGE = "WORKSPACE_MANAGE"  # 工作空间管理
    WORKSPACE_PERMISSION_MANAGE = "WORKSPACE_PERMISSION_MANAGE"

    # 工作空间维度
    WORKSPACE = "WORKSPACE"
    WORKSPACE_WORKER_MANAGE = "WORKSPACE_WORKER_MANAGE"
    WORKER_MANAGED_OBJECT_MANAGE = "WORKER_MANAGED_OBJECT_MANAGE"
    MANAGED_OBJECT_PERMISSION_MANAGE = "MANAGED_OBJECT_PERMISSION_MANAGE"

    # object
    MANAGED_OBJECT_CHANGELOG_MANAGE = "MANAGED_OBJECT_CHANGELOG_MANAGE"
    MANAGED_OBJECT_SECRET_MANAGE = "MANAGED_OBJECT_SECRET_MANAGE"

    @staticmethod
    def check_workspace(module) -> bool:
        return (
            module == PermissionModule.WORKSPACE_WORKER_MANAGE.name
            or module == PermissionModule.WORKER_MANAGED_OBJECT_MANAGE.name
            or module == PermissionModule.MANAGED_OBJECT_PERMISSION_MANAGE.name
            or module == PermissionModule.MANAGED_OBJECT_CHANGELOG_MANAGE.name
        )

    @staticmethod
    def check_object(module) -> bool:
        return (
            module == PermissionModule.MANAGED_OBJECT_CHANGELOG_MANAGE.name
            or module == PermissionModule.MANAGED_OBJECT_SECRET_MANAGE.name
        )


def extract_version(name):
    match = re.search(r"(\d+\.\d+(?:\.\d+){0,2})(?:-([a-zA-Z0-9]+))?", name)
    if match:
        # 将版本号分割为整数元组，例如 '1.2.3' -> (1, 2, 3)
        version_numbers = tuple(map(int, match.group(1).split(".")))
        suffix = match.group(2) or ""
        return version_numbers, suffix
    return (0,), ""  # 默认返回最小版本
