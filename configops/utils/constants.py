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


def parse_args(input_args: str) -> list:
    """
    Parse input args string to list
    """
    result = []
    buffer = []
    inside_quotes = False

    for char in input_args:
        if char == '"':  # 切换双引号状态
            inside_quotes = not inside_quotes
            buffer.append(char)  # 保留双引号
        elif char == " " and not inside_quotes:  # 遇到空格且不在双引号内
            if buffer:
                result.append("".join(buffer))
                buffer = []
        else:
            buffer.append(char)

    if buffer:
        result.append("".join(buffer))

    return result
