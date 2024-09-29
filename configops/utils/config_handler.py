import io
import logging
import configobj
import json
from configops.utils import constants
from configops.utils.exception import ConfigOpsException
from ruamel import yaml as ryaml
import xml.etree.ElementTree as ET

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
        if format == constants.PROPERTIES:
            raise ex

    # 尝试当yaml解析
    try:
        yaml = ryaml.YAML()
        yaml.preserve_quotes = True
        data = yaml.load(content)
        return constants.YAML, data, yaml
    except Exception as ex:
        if format == constants.YAML:
            raise ex

    # 尝试当json解析
    try:
        data = json.load(content)
        return constants.JSON, data, None
    except Exception as ex:
        if format == constants.JSON:
            raise ex

    # 尝试当xml解析
    try:
        data = ET.fromstring(content)
        return constants.XML, data, None
    except ET.ParseError as ex:
        if format == constants.XML:
            raise ex

    return constants.UNKNOWN, None, None


def patch(patch, current, format):
    if format == constants.YAML:
        yaml_patch(patch=patch, current=current)
    elif format == constants.PROPERTIES:
        properties_patch(patch=patch, current=current)
    else:
        raise ConfigOpsException(f"Patch unsupported format: {format}")


def to_string(format, current, y):
    if format == constants.YAML:
        return yaml_to_string(current, y)
    elif format == constants.PROPERTIES:
        return properties_to_string(current)
    else:
        raise ConfigOpsException(f"ToString unsupported format: {format}")


def yaml_cpx(full, current):
    """
    YAML 相关方法
    """
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
                value = patch[key]
                current_value = current[key]
                if value is None:
                    del current[key]
                if isinstance(current_value, dict) and isinstance(value, dict):
                    yaml_delete(value, current_value)
                elif not isinstance(current_value, dict) and not isinstance(
                    value, dict
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


def patch_by_str(content, edit, type):
    needPatch = True
    if len(content.strip()) == 0:
        needPatch = False
        if len(edit.strip()) == 0:
            return {
                "format": type,
                "content": "",
                "nextContent": "",
            }
        format, current, yml = parse_content(edit, format=type)
    else:
        format, current, yml = parse_content(content, format=type)

    if needPatch:
        if format == constants.YAML:
            suc, msg = yaml_patch_content(edit, current)
            if suc is False:
                raise ConfigOpsException(f"yaml patch error. {msg}")
            return {
                "format": format,
                "content": content,
                "nextContent": yaml_to_string(current, yml),
            }
        elif format == constants.PROPERTIES:
            suc, msg = properties_patch_content(edit, current)
            if suc is False:
                raise ConfigOpsException(f"yaml patch error. {msg}")
            return {
                "format": format,
                "content": content,
                "nextContent": properties_to_string(current),
            }
        else:
            raise ConfigOpsException(f"Unsupport patch format. {type}")
    else:
        if format == constants.UNKNOWN:
            format = constants.TEXT
        return {"format": format, "content": content, "nextContent": edit}


def delete_by_str(content, edit, type):
    if len(content.strip()) == 0:
        return {"format": type, "content": "", "nextContent": ""}
    format, current, yml = parse_content(content, format=type)
    if format == constants.YAML:
        suc, msg = yaml_delete_content(edit, current)
        if suc is False:
            raise ConfigOpsException(f"yaml delete error. {msg}")
        return {
            "format": format,
            "content": content,
            "nextContent": yaml_to_string(current, yml),
        }
    elif format == constants.PROPERTIES:
        suc, msg = properties_delete_content(edit, current)
        if suc is False:
            raise ConfigOpsException(f"properties delete error. {msg}")
        return {
            "format": format,
            "content": content,
            "nextContent": properties_to_string(current),
        }
    else:
        raise ConfigOpsException(f"Unsupported delete format. {format}")


def delete_patch_by_str(content, type, deleteContent="", patchContent=""):
    delete_res = delete_by_str(
        content,
        deleteContent,
        type,
    )
    res = patch_by_str(
        delete_res["nextContent"],
        patchContent,
        type,
    )
    return res
