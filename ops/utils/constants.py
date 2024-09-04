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


def is_support_format(format):
    return format == PROPERTIES or format == YAML
