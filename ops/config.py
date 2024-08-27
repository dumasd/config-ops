""" 配置文件 """

from ruamel.yaml import YAML
from ops.utils.constants import CONFIG_ENV_NAME, CONFIG_FILE_ENV_NAME
from marshmallow import Schema, fields, ValidationError
import os
import logging

logger = logging.getLogger(__name__)


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
    dialect = fields.Str(required=False, default="mysql")


def load_config(config_file=None):
    """加载YAML配置"""
    yaml = YAML()
    # 尝试读取配置文件
    if config_file is None or len(config_file.strip()) == 0:
        config_file = os.getenv(CONFIG_FILE_ENV_NAME)

    if config_file is not None and len(config_file.strip()) > 0:
        print(f"Load config from file: {config_file}")
        with open(config_file, "r") as file:
            config = yaml.load(file)
        return config

    conf_val = os.getenv(CONFIG_ENV_NAME)
    if conf_val is not None and len(conf_val.strip()) > 0:
        print(f"Load config enviroment: {CONFIG_ENV_NAME}")
        config = yaml.load(conf_val)
        return config
    return None
