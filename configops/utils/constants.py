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


class CHANGE_LOG_EXEXTYPE(Enum):
    INIT = "INIT"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    # RERUN = "RERUN"

    def matches(self, value):
        return self.value == value


class SYSTEM_TYPE(Enum):
    NACOS = "NACOS"
    DATABASE = "DATABASE"
    REDIS = "REDIS"


DIALECT_DRIVER_MAP = {
    "mysql": "mysqlconnector",
    "postgresql": "psycopg2",
}


def extract_version(name):
    match = re.search(r"(\d+\.\d+(?:\.\d+){0,2})(?:-([a-zA-Z0-9]+))?", name)
    if match:
        # 将版本号分割为整数元组，例如 '1.2.3' -> (1, 2, 3)
        version_numbers = tuple(map(int, match.group(1).split(".")))
        suffix = match.group(2) or ""
        return version_numbers, suffix
    return (0,), ""  # 默认返回最小版本
