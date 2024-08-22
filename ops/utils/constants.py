PROPERTIES = "properties"
YAML = "yaml"
UNKNOWN = "unknown"

CONFIG_ENV_NAME = "CONFIGOPS_CONFIG"

def is_support_format(format):
    return format == PROPERTIES or format == YAML
        