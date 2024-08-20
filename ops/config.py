""" 配置文件 """

from ruamel.yaml import YAML
from marshmallow import Schema, fields, ValidationError


class Config:
    NACOS_CONFIGS = {
        "default": {
            "url": "http://localhost:8848",
            "username": "nacos",
            "password": "nacos",
            "blacklist": [
                {"namespace": "public", "group": "DEFAULT_GROUP", "dataId": "sss:ssss"}
            ],
        },
        "nacos1": {
            "url": "http://localhost:8848",
            "username": "nacos",
            "password": "nacos",
        },
    }


class DbConfig(Schema):
    url = fields.Str(required=True, default="localhost")
    port = fields.Integer(required=True, default=3306)
    username = fields.Str(required=True)
    password = fields.Str(required=True)


""" 加载YAML配置 """


def load_config(config_file="config.yaml"):
    yaml = YAML()
    with open(config_file, "r") as file:
        config = yaml.load(file)
    return config
