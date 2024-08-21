PROPERTIES = "properties"
YAML = "yaml"
UNKNOWN = "unknown"


def is_support_format(format):
    return format == PROPERTIES or format == YAML
        