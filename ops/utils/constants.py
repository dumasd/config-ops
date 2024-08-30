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


CHANGE_LOG_EXEXTYPE_EXECUTED = "EXECUTED"


class CHANGE_LOG_EXEXTYPE(str, Enum):
    INIT = "INIT"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    # RERUN = "RERUN"

    def matches(self, value: str | None) -> bool:
        return self.value == value


class SYSTEM_TYPE(str, Enum):
    NACOS = "NACOS"
    DATABASE = "DATABASE"
    REDIS = "REDIS"


DIALECT_DRIVER_MAP = {
    "mysql": "mysqlconnector",
    "postgresql": "psycopg2",
}


def is_support_format(format):
    return format == PROPERTIES or format == YAML
