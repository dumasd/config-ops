# -*- coding: utf-8 -*-
from typing import Optional
from flask import current_app
from ruamel.yaml import YAML
from configops.utils.constants import CONFIG_ENV_NAME, CONFIG_FILE_ENV_NAME, SystemType
from marshmallow import Schema, fields, validate, ValidationError, EXCLUDE
import os
import logging
import re

logger = logging.getLogger(__name__)


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


class ProvisionConfig(Schema):
    enabled = fields.Bool(required=True)
    ipsource = fields.Str(required=False)
    permissions = fields.Str(required=True)


class DbConfig(Schema):
    url = fields.Str(required=True, dump_default="localhost")
    host = fields.Str(required=False, dump_default="localhost")
    port = fields.Integer(required=True, dump_default=3306)
    dialect = fields.Str(required=False, dump_default="mysql")
    changelogschema = fields.Str(required=False, dump_default="liquibase")
    username = fields.Str(required=True)
    password = fields.Str(required=False)
    secretmanager = fields.Nested(SecretManager, required=False)
    provision = fields.Nested(ProvisionConfig, required=False)


class NacosConfig(Schema):
    url = fields.Str(required=True, dump_default="http://localhost:8848")
    username = fields.Str(required=False)
    password = fields.Str(required=False)
    secretmanager = fields.Nested(SecretManager, required=False)


class EsConfig(Schema):
    url = fields.Str(required=True)
    username = fields.Str(required=False)
    password = fields.Str(required=False)
    api_id = fields.Str(required=False)
    api_key = fields.Str(required=False)
    secretmanager = fields.Nested(SecretManager, required=False)


class GraphdbConfig(Schema):
    dialect = fields.Str(required=True)
    host = fields.Str(required=True)
    port = fields.Integer(required=True)
    username = fields.Str(required=False)
    password = fields.Str(required=False)
    secure = fields.Boolean(required=False)
    secretmanager = fields.Nested(SecretManager, required=False)


class NodeConfig(Schema):
    """
    Node Configuration
    """

    role = fields.Str(
        required=False,
        dump_default="worker",
        validate=validate.OneOf(["controller", "worker"]),
    )
    controller_url = fields.Str(required=False, validate=validate.URL())
    secret = fields.Str(required=False)
    name = fields.Str(required=False)


class OidcConfig(Schema):
    """
    OIDC Configuration
    """

    enabled = fields.Bool(required=False, dump_default=False)
    client_id = fields.Str(required=True)
    client_secret = fields.Str(required=True)
    issuer = fields.Str(required=True, validate=validate.URL())
    scope = fields.Str(required=False, dump_default="openid profile email")
    groups_sync = fields.Str(required=False)
    auto_login = fields.Bool(required=False, dump_default=False)
    login_txt = fields.Str(required=False, load_default="Sign in with OIDC")


class AuthConfig(Schema):
    oidc = fields.Nested(OidcConfig, required=False)


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


def get_config(app, key: str, default=None):
    # 匹配字段名和索引，如 bbb[0][1] -> bbb, 0, 1
    tokens = re.findall(r"([a-zA-Z0-9_]+)|\[(\d+)\]", key)
    data = app.config
    try:
        for name, idx in tokens:
            if name:
                data = data[name]
            elif idx:
                data = data[int(idx)]
        return data
    except (KeyError, IndexError, TypeError):
        return default


def get_aws_cfg():
    """
    Get AWS configuration
    """
    aws_cfg = current_app.config.get("aws", None)
    if aws_cfg is None:
        return None
    else:
        schema = AwsConfig()
        return schema.load(aws_cfg)


def get_nacos_cfg(nacos_id):
    """
    Get Nacos configuration

    :type nacos_id: str
    :param nacos_id: nacos id

    :rtype: map
    :return: nacos info
    """
    cfg = get_config(current_app, f"nacos.{nacos_id}")
    if cfg is None:
        return None
    schmea = NacosConfig()
    return schmea.load(cfg)


def get_database_cfg(app, db_id):
    """
    Get database configuration

    :type db_id: str
    :param db_id: database id

    :rtype: map
    :return: database info
    """
    db_cfg = get_config(app, f"database.{db_id}")
    if db_cfg == None:
        return None
    schema = DbConfig()
    return schema.load(db_cfg)


def get_elasticsearch_cfg(es_id):
    """
    Get elasticsearch configuration

    :type db_id: str
    :param db_id: database id

    :rtype: map
    :return: database info
    """
    cfg = get_config(current_app, f"elasticsearch.{es_id}")
    if cfg == None:
        return None
    data = EsConfig().load(cfg)
    return data


def get_graphdb_cfg(system_id):
    """
    Get graphdb configuration

    :type system_id: str
    :param system_id: system_id

    :rtype: map
    :return: database info
    """
    cfg = get_config(current_app, f"graphdb.{system_id}")
    if cfg == None:
        return None
    data = GraphdbConfig().load(cfg)
    return data


def get_java_home_dir(app):
    """
    Get java_home dir
    """
    java_home = get_config(app, "config.java-home-dir")
    if java_home:
        return java_home
    java_home = get_config(app, "config.java_home_dir")
    if java_home:
        return java_home
    return None


def get_liquibase_cfg(app):
    """
    Get liquibase configuration
    """
    return get_config(app, "config.liquibase")


def get_node_cfg(app):
    cfg = get_config(app, "config.node")
    if cfg:
        schema = NodeConfig()
        return schema.load(cfg)
    else:
        return {"role": "worker"}


def get_auth_config(app):
    auth_cfg = get_config(app, "config.auth")
    if auth_cfg:
        schema = AuthConfig()
        return schema.load(auth_cfg)


def get_object_url(app, system_id, system_type: SystemType) -> Optional[str]:
    key = system_type.name.lower()
    cfg = get_config(app, f"{key}.{system_id}")
    if cfg is None:
        return ""
    if system_type == SystemType.NACOS or system_type == SystemType.ELASTICSEARCH:
        return cfg.get("url")
    elif system_type == SystemType.DATABASE:
        host = cfg.get("url")
        port = cfg.get("port")
        return f"{host}:{port}"
    elif system_type == SystemType.GRAPHDB:
        host = cfg.get("host")
        port = cfg.get("port")
        return f"{host}:{port}"
    else:
        return ""
