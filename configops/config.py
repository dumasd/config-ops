# -*- coding: utf-8 -*-
import os
import logging
import re
from typing import Optional
from flask import current_app
from ruamel.yaml import YAML
from jsonschema import Draft7Validator
from marshmallow import Schema, fields, validate
from configops.utils.constants import CONFIG_ENV_NAME, CONFIG_FILE_ENV_NAME, SystemType
from configops.utils.exception import ConfigOpsException


logger = logging.getLogger(__name__)


CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "logging": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "default": "INFO",
                    "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    "description": "Logging level, e.g., DEBUG, INFO, WARNING, ERROR, CRITICAL",
                },
                "format": {
                    "type": "string",
                    "default": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    "description": "Log message format",
                },
            },
        },
        "nacos": {
            "type": "object",
            "description": "Nacos configurations",
            "patternProperties": {
                "^.*$": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "pattern": r"^https?://[^:/\s]+:\d+$",
                            "description": "Nacos server URL and the port is required. Example: http://localhost:8848, https://nacos.example.com:443",
                        },
                        "username": {
                            "type": "string",
                            "description": "Nacos username",
                        },
                        "password": {
                            "type": "string",
                            "description": "Nacos password",
                        },
                        "secretmanager": {"$ref": "#/definitions/SecretManager"},
                    },
                    "required": ["url"],
                }
            },
        },
        "database": {
            "type": "object",
            "description": "Database configurations",
            "patternProperties": {
                "^.*$": {
                    "type": "object",
                    "properties": {
                        "dialect": {
                            "type": "string",
                            "enum": ["mysql", "postgresql"],
                            "description": "Database dialect. Example: mysql",
                        },
                        "url": {
                            "type": "string",
                            "description": "Database url. Example: localhost",
                        },
                        "port": {
                            "type": ["string", "number"],
                            "description": "Database port. Example: 5432",
                        },
                        "username": {
                            "type": "string",
                            "description": "Database username",
                        },
                        "password": {
                            "type": "string",
                            "description": "Database password",
                        },
                        "secretmanager": {"$ref": "#/definitions/SecretManager"},
                    },
                    "required": ["dialect", "url", "port"],
                }
            },
        },
        "elasticsearch": {
            "type": "object",
            "description": "Elasticsearch configurations",
            "patternProperties": {
                "^.*$": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "format": "uri",
                            "description": "Elasticsearch url. Example: http://localhost:9200",
                        },
                        "username": {
                            "type": "string",
                            "description": "Elasticsearch username",
                        },
                        "password": {
                            "type": "string",
                            "description": "Elasticsearch password",
                        },
                        "api_id": {
                            "type": "string",
                            "description": "Elasticsearch8.X API ID",
                        },
                        "api_key": {
                            "type": "string",
                            "description": "Elasticsearch8.X API Key",
                        },
                        "secretmanager": {"$ref": "#/definitions/SecretManager"},
                    },
                    "required": ["url"],
                }
            },
        },
        "graphdb": {
            "type": "object",
            "description": "Graphdb configurations",
            "patternProperties": {
                "^.*$": {
                    "type": "object",
                    "properties": {
                        "dialect": {
                            "type": "string",
                            "enum": ["neptune", "neo4j", "jenafuseki", "janusgraph"],
                            "description": "Graphdb dialect. Example: neptune",
                        },
                        "host": {
                            "type": "string",
                            "description": "Graphdb host. Example: localhost",
                        },
                        "port": {
                            "type": ["string", "number"],
                            "description": "Graphdb port. Example: 8182",
                        },
                        "username": {
                            "type": "string",
                            "description": "Graphdb username",
                        },
                        "password": {
                            "type": "string",
                            "description": "Graphdb password",
                        },
                        "aws_iam_authentication": {
                            "type": "object",
                            "description": "AWS IAM authentication configurations",
                            "properties": {
                                "enabled": {
                                    "type": "boolean",
                                    "default": False,
                                    "description": "Enable AWS IAM authentication",
                                },
                                "region": {
                                    "type": "string",
                                    "description": "AWS region for IAM authentication",
                                },
                                "access_key": {
                                    "type": "string",
                                    "description": "AWS access key ID for IAM authentication",
                                },
                                "secret_key": {
                                    "type": "string",
                                    "description": "AWS secret access key for IAM authentication",
                                },
                            },
                        },
                        "secretmanager": {"$ref": "#/definitions/SecretManager"},
                    },
                    "required": ["dialect", "host"],
                }
            },
        },
        "aws": {
            "type": "object",
            "description": "AWS configurations",
            "properties": {
                "credentials": {
                    "type": "string",
                    "default": "~/.aws/credentials",
                    "description": "Path to AWS credentials file",
                },
                "config": {
                    "type": "string",
                    "default": "~/.aws/config",
                    "description": "Path to AWS config file",
                },
                "access_key": {
                    "type": "string",
                    "description": "AWS access key ID",
                },
                "secret_key": {
                    "type": "string",
                    "description": "AWS secret access key",
                },
                "region": {
                    "type": "string",
                    "description": "AWS region. Example: us-west-2",
                },
            },
        },
        "config": {
            "type": "object",
            "description": "Application own configuration",
            "properties": {
                "home_url": {
                    "type": "string",
                    "description": "Home URL of the application",
                },
                "auth": {
                    "type": "object",
                    "description": "Authentication configurations",
                    "properties": {
                        "oidc": {
                            "type": "object",
                            "description": "OIDC configurations",
                            "properties": {
                                "enabled": {
                                    "type": "boolean",
                                    "default": False,
                                    "description": "Enable OIDC authentication",
                                },
                                "client_id": {
                                    "type": "string",
                                    "description": "OIDC client ID",
                                },
                                "client_secret": {
                                    "type": "string",
                                    "description": "OIDC client secret",
                                },
                                "issuer": {
                                    "type": "string",
                                    "format": "uri",
                                    "description": "OIDC issuer URL",
                                },
                                "scope": {
                                    "type": "string",
                                    "default": "openid profile email",
                                    "description": "OIDC scope",
                                },
                                "groups_sync": {
                                    "type": ["string", "null"],
                                    "description": "Groups sync configuration, e.g., group1,group2",
                                },
                                "auto_login": {
                                    "type": "boolean",
                                    "default": False,
                                    "description": "Enable auto login with OIDC",
                                },
                                "login_txt": {
                                    "type": ["string", "null"],
                                    "default": None,
                                    "description": "Text for OIDC login button",
                                },
                            },
                            "required": ["client_id", "client_secret", "issuer"],
                        }
                    },
                },
                "node": {
                    "type": "object",
                    "description": "Node configurations",
                    "properties": {
                        "role": {
                            "type": "string",
                            "default": "worker",
                            "enum": ["controller", "worker"],
                            "description": "Node role, either controller or worker",
                        },
                        "name": {
                            "type": ["string", "null"],
                            "description": "Name of the node",
                        },
                        "controller_url": {
                            "type": ["string", "null"],
                            "format": "uri",
                            "description": "Controller URL for worker nodes",
                        },
                        "secret": {
                            "type": ["string", "null"],
                            "description": "Secret for node communication",
                        },
                    },
                },
                "redis_uri": {
                    "type": ["string", "null"],
                    "format": "uri",
                    "default": "redis://localhost:6379/0",
                    "description": "Redis connection URI",
                },
                "database-uri": {
                    "type": "string",
                    "default": "sqlite:///configops.db",
                    "description": "Database connection URI",
                },
                "java-home-dir": {
                    "type": ["string", "null"],
                    "description": "Java home directory path",
                },
                "liquibase": {
                    "type": "object",
                    "description": "Liquibase configurations",
                    "properties": {
                        "defaults-file": {
                            "type": ["string", "null"],
                            "default": "",
                            "description": "Liquibase defaults file path",
                        },
                        "jdbc-drivers-dir": {
                            "type": ["string", "null"],
                            "default": "jdbc-drivers",
                            "description": "Path to the JDBC drivers directory for Liquibase",
                        },
                    },
                },
            },
        },
    },
    "definitions": {
        "SecretManager": {
            "type": "object",
            "description": "Secret manager configurations",
            "properties": {
                "aws": {
                    "type": "object",
                    "description": "AWS Secret Manager configurations",
                    "properties": {
                        "profile": {
                            "type": "string",
                            "default": "default",
                            "description": "AWS profile name for secret manager",
                        },
                        "secretid": {
                            "type": "string",
                            "description": "AWS Secret ID for secret manager",
                        },
                    },
                    "required": ["secretid"],
                }
            },
        },
    },
    "required": ["config"],
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
    yaml = YAML()
    config_data = None

    # Try to get config from environment config file
    if config_file is None or len(config_file.strip()) == 0:
        config_file = os.getenv(CONFIG_FILE_ENV_NAME)
    if config_file and os.path.isfile(config_file):
        print(f"Load config from file: {config_file}")
        with open(config_file, "r", encoding="utf-8") as file:
            config_data = yaml.load(file)

    # Try to get config from environment config value
    if config_data is None:
        conf_val = os.getenv(CONFIG_ENV_NAME)
        if conf_val and len(conf_val.strip()) > 0:
            print(f"Load config enviroment: {CONFIG_ENV_NAME}")
            config_data = yaml.load(conf_val)

    # Try to get config from config.yaml in running path
    if config_data is None:
        config_file = "config.yaml"
        if os.path.isfile(config_file):
            print(f"Load config from file: {config_file}")
            with open(config_file, "r", encoding="utf-8") as file:
                config_data = yaml.load(file)

    if config_data:
        errors = validate_config(config_data)
        if len(errors) > 0:
            error_log_text = "Invalid configuration details [key: error message]:\n"
            for error in errors:
                error_log_text += f"    - {error['key']}: {error['message']}\n"
            logger.error(error_log_text)
            raise ConfigOpsException(
                "Invalid configuration, please check the logs for the details."
            )

    return config_data


def validate_config(config_data) -> list:
    """
    Validate the configuration data against the schema.
    """
    validator = Draft7Validator(CONFIG_SCHEMA)
    errors = []
    for error in validator.iter_errors(config_data):
        key_path = ".".join(map(str, error.path))
        error_message = error.message
        errors.append(
            {
                "key": key_path,
                "message": error_message,
            }
        )
    return errors


def get_config(app, key: str, default=None):
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
