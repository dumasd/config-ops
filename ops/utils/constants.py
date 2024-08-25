PROPERTIES = "properties"
YAML = "yaml"
JSON = "json"
XML = "xml"
UNKNOWN = "unknown"

CONFIG_ENV_NAME = "CONFIGOPS_CONFIG"
CONFIG_FILE_ENV_NAME = "CONFIGOPS_CONFIG_FILE"

def is_support_format(format):
    return format == PROPERTIES or format == YAML
        