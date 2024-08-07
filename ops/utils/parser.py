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
            io.StringIO(content), encoding="utf-8", list_values=False
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
YAML: 根据当前全量配置，删除不存在的配置
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
    # elif isinstance(current, list) and isinstance(full, list):
    # list 忽略，暂时没办法判断


"""
YAML: 根据增量配置，替换值或者新增配置
"""


def yaml_patch(patch, current):
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


def yaml_to_string(data, yaml):
    output_stream = io.StringIO()
    yaml.dump(data, output_stream)
    return output_stream.getvalue()


"""
PROPERTIES 相关方法
"""


def properties_to_string(data):
    output_stream = io.BytesIO()
    data.write(output_stream)
    t = output_stream.getvalue()
    return t.decode()


"""
PROPERTIES: 根据当前全量配置移除多余配置
"""


def properties_cpx(full, current):
    keys_to_remove = []
    for key in current:
        if key not in full:
            keys_to_remove.append(key)
        elif isinstance(current[key], dict) and isinstance(full[key], dict):
            properties_cpx(full[key], current[key])
    for key in keys_to_remove:
        del current[key]


"""PROPERTIES: 追加配置"""


def properties_patch(patch, current):
    for key in current:
        if key in patch:
            if isinstance(current[key], dict) and isinstance(patch[key], dict):
                properties_patch(patch[key], current[key])
            else:
                current[key] = patch[key]
