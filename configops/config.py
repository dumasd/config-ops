""" 配置文件 """

from flask import current_app
from ruamel.yaml import YAML
from configops.utils.constants import CONFIG_ENV_NAME, CONFIG_FILE_ENV_NAME
from marshmallow import Schema, fields, ValidationError, EXCLUDE
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


class AwsConfig(Schema):
    credentials = fields.Str(required=False)
    config = fields.Str(required=False)
    access_key = fields.Str(required=False)
    secret_key = fields.Str(required=False)
    region = fields.Str(required=False)


class AwsSecretManager(Schema):
    profile = fields.Str(required=False, dump_default="default")
    secretid = fields.Str(required=True)


class SecretManager(Schema):
    aws = fields.Nested(AwsSecretManager, required=False)


class DbConfig(Schema):
    url = fields.Str(required=True, dump_default="localhost")
    host = fields.Str(required=False, dump_default="localhost")
    port = fields.Integer(required=True, dump_default=3306)
    dialect = fields.Str(required=False, dump_default="mysql")
    changelogschema = fields.Str(required=False, dump_default="liquibase")
    username = fields.Str(required=True)
    password = fields.Str(required=False)
    secretmanager = fields.Nested(SecretManager, required=False)


class NacosConfig(Schema):
    url = fields.Str(required=True, dump_default="http://localhost:8848")
    username = fields.Str(required=False)
    password = fields.Str(required=False)
    secretmanager = fields.Nested(SecretManager, required=False)


def load_config(config_file=None):
    """加载YAML配置"""
    yaml = YAML()
    # 尝试读取配置文件
    if config_file is None or len(config_file.strip()) == 0:
        config_file = os.getenv(CONFIG_FILE_ENV_NAME)

    if config_file and os.path.isfile(config_file):
        print(f"Load config from file: {config_file}")
        with open(config_file, "r", encoding="utf-8") as file:
            config = yaml.load(file)
        return config

    conf_val = os.getenv(CONFIG_ENV_NAME)
    if conf_val and len(conf_val.strip()) > 0:
        print(f"Load config enviroment: {CONFIG_ENV_NAME}")
        config = yaml.load(conf_val)
        return config

    # 读取默认的config.yaml
    config_file = "config.yaml"
    if os.path.isfile(config_file):
        print(f"Load config from file: {config_file}")
        with open(config_file, "r", encoding="utf-8") as file:
            config = yaml.load(file)
        return config

    return None


def get_aws_cfg():
    """
    获取AWS配置
    """
    aws_cfg = current_app.config.get("aws", None)
    if aws_cfg is None:
        return None
    else:
        schema = AwsConfig()
        return schema.load(aws_cfg)


def get_nacos_cfg(nacos_id):
    """
    Get Nacos info

    :type nacos_id: str
    :param nacos_id: nacos id

    :rtype: map
    :return: nacos info
    """
    nacos_cfgs = current_app.config["nacos"]
    nacos_cfg = nacos_cfgs[nacos_id]
    if nacos_cfg is None:
        return None
    schmea = NacosConfig()
    return schmea.load(nacos_cfg)


def get_database_cfg(db_id):
    """
    Get database info

    :type db_id: str
    :param db_id: database id

    :rtype: map
    :return: database info
    """
    db_cfgs = current_app.config["database"]
    db_cfg = db_cfgs.get(db_id, None)
    if db_cfg == None:
        return None
    schema = DbConfig()
    return schema.load(db_cfg)


def get_java_home_dir(app):
    """
    获取java_home 路径
    """
    cfg = app.config.get("config")
    if cfg:
        java_home = cfg.get("java-home-dir")
        if java_home and len(java_home.strip()) > 0:
            return java_home
    return None


def get_liquibase_cfg(app):
    """
    获取liquibase配置
    """
    cfg = app.config.get("config")
    if cfg:
        liquibase_cfg = cfg.get("liquibase")
        return liquibase_cfg
    return None
