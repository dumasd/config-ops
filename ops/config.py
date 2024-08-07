""" 配置文件 """
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