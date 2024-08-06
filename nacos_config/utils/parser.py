import io
import logging
import configobj
from nacos_config.utils import constants
from ruamel import yaml as ryaml

logger = logging.getLogger(__name__)

def parse_content(content):
    # 尝试当properties解析
    try:
        prop = configobj.ConfigObj(io.StringIO(content), encoding='utf-8')
        return constants.PROPERTIES, prop, None
    except Exception as ex:
        logger.warning(f'非properties文件{ex}')  
    
    # 尝试当yaml解析
    try:
        yaml = ryaml.YAML()
        yaml.preserve_quotes = True
        data = yaml.load(content)
        return constants.YAML, data, yaml
    except Exception as ex:
        logger.warning(f'非yaml文件{ex}')
    
    return constants.UNKNOWN, None

"""
根据当前全量配置，删除不存在的配置
"""
def yaml_remove_extra_keys(full, current):
    # 只支持dict
    if isinstance(current, dict) and isinstance(full, dict):
        keys_to_remove = []
        for key in current:
            if key not in full:
                keys_to_remove.append(key)
            else:
                yaml_remove_extra_keys(full[key], current[key])
        for key in keys_to_remove:
            del current[key]
    #elif isinstance(current, list) and isinstance(full, list):
        # list 忽略，暂时没办法判断

"""
根据增量配置，替换值或者新增配置
"""
def yaml_patch(patch, current):
    if isinstance(current, dict) and isinstance(patch, dict):
        for key in patch:
            if key in current:
                if isinstance(current[key], dict) and isinstance(patch[key], dict):
                    yaml_patch(patch[key], current[key])
                elif not isinstance(current[key], dict) and not isinstance(patch[key], dict):
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
