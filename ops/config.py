""" 配置文件 """
from ruamel.yaml import YAML

class Config:
    NACOS_CONFIGS = {
        'default': {
            'url': 'http://localhost:8848',
            'username': 'nacos',
            'password': 'nacos',
            'blacklist': [
                {'namespace': 'public', 'group': 'DEFAULT_GROUP', 'dataId': 'sss:ssss'}
            ],
        },
        'nacos1': {
            'url': 'http://localhost:8848',
            'username': 'nacos',
            'password': 'nacos'
        }
    }

""" 加载YAML配置 """
def load_config(config_file='config.yaml'):
    yaml = YAML()
    with open(config_file, 'r') as file:
        config = yaml.load(file)     
    return config           