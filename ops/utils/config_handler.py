import io
import logging
import configobj
from ops.utils import constants
from ruamel import yaml as ryaml

logger = logging.getLogger(__name__)


def parse_content(content: str, format=None):
    # 尝试当properties解析
    try:
        prop = configobj.ConfigObj(
            io.StringIO(content),
            encoding="utf-8",
            list_values=False,
            raise_errors=True,
            write_empty_values=True,
        )
        return constants.PROPERTIES, prop, None
    except BaseException as ex:
        logger.warning(f"非properties文件{ex}")
        if format == constants.PROPERTIES:
            raise ex

    # 尝试当yaml解析
    try:
        yaml = ryaml.YAML()
        yaml.preserve_quotes = True
        data = yaml.load(content)
        return constants.YAML, data, yaml
    except Exception as ex:
        logger.warning(f"非yaml文件{ex}")
        if format == constants.YAML:
            raise ex

    return constants.UNKNOWN, None


"""
YAML 相关方法
"""


def yaml_cpx(full, current):
    # 只支持dict
    if isinstance(current, dict) and isinstance(full, dict):
        keys_to_remove = []
        for key in current:
            if key not in full:
                keys_to_remove.append(key)
            else:
                yaml_cpx(full[key], current[key])
        for key in keys_to_remove:
            del current[key]
        for key in full:
            if key not in current:
                current[key] = full[key]
    # elif isinstance(current, list) and isinstance(full, list):
    # list 忽略，暂时没办法判断


def yaml_patch(patch, current):
    """
    将Patch的内容追加或修改到Current
    """
    if isinstance(current, dict) and isinstance(patch, dict):
        for key in patch:
            if key in current:
                if isinstance(current[key], dict) and isinstance(patch[key], dict):
                    yaml_patch(patch[key], current[key])
                elif not isinstance(current[key], dict) and not isinstance(
                    patch[key], dict
                ):
                    current[key] = patch[key]
            else:
                current[key] = patch[key]


def yaml_delete(patch, current):
    """
    从Current中删除Delete的内容
    """
    if isinstance(current, dict) and isinstance(patch, dict):
        for key in patch:
            if key in current:
                if isinstance(current[key], dict) and isinstance(patch[key], dict):
                    yaml_delete(patch[key], current[key])
                elif not isinstance(current[key], dict) and not isinstance(
                    patch[key], dict
                ):
                    del current[key]


def yaml_to_string(data, yaml):
    output_stream = io.StringIO()
    yaml.dump(data, output_stream)
    return output_stream.getvalue()


def yaml_cpx_content(full_content, current):
    if full_content is not None and len(full_content.strip()) > 0:
        try:
            _, full, _ = parse_content(full_content, constants.YAML)
            yaml_cpx(full, current)
        except BaseException:
            return False, "Full content must be yaml"
    return True, "OK"


def yaml_patch_content(patch_content, current):
    if patch_content is not None and len(patch_content.strip()) > 0:
        try:
            _, patch, _ = parse_content(patch_content, format=constants.YAML)
            yaml_patch(patch, current)
        except BaseException:
            return False, "Full content must be yaml"
    return True, "OK"


def yaml_delete_content(delete_content, current):
    if delete_content is not None and len(delete_content.strip()) > 0:
        try:
            _, delete, _ = parse_content(delete_content, format=constants.YAML)
            yaml_delete(delete, current)
        except BaseException:
            return False, "Full content must be yaml"
    return True, "OK"


"""
PROPERTIES 相关方法
"""


def properties_to_string(data):
    output_stream = io.BytesIO()
    data.write(output_stream)
    t = output_stream.getvalue()
    return t.decode()


def properties_cpx(full, current):
    keys_to_remove = []
    for key in current:
        if key not in full:
            keys_to_remove.append(key)
        elif isinstance(current[key], dict) and isinstance(full[key], dict):
            properties_cpx(full[key], current[key])
    for key in keys_to_remove:
        del current[key]


def properties_patch(patch, current):
    for key in current:
        if key in patch:
            if isinstance(current[key], dict) and isinstance(patch[key], dict):
                properties_patch(patch[key], current[key])
            else:
                current[key] = patch[key]
    for key in patch:
        if key not in current:
            current[key] = patch[key]


def properties_delete(patch, current):
    for key in patch:
        if key in current:
            del current[key]


def properties_cpx_content(full_content, current):
    if full_content is not None and len(full_content.strip()) > 0:
        try:
            _, full, _ = parse_content(full_content, constants.PROPERTIES)
            properties_cpx(full, current)
        except BaseException:
            return False, "Full content must be properties"
    return True, "OK"


def properties_patch_content(patch_content, current):
    if patch_content is not None and len(patch_content.strip()) > 0:
        try:
            _, patch, _ = parse_content(patch_content, format=constants.PROPERTIES)
            properties_patch(patch, current)
        except BaseException:
            return False, "Patch content must be properties"
    return True, "OK"


def properties_delete_content(delete_content, current):
    if delete_content is not None and len(delete_content.strip()) > 0:
        try:
            _, delete, _ = parse_content(delete_content, format=constants.PROPERTIES)
            properties_delete(delete, current)
        except BaseException:
            return False, "Patch content must be properties"
    return True, "OK"
