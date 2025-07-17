import logging
from enum import Enum
from typing import Optional
import sqlalchemy
from flask import current_app
from sqlalchemy.exc import DBAPIError
import base64
from configops.database.utils import create_database_engine
from configops.database.db import db, ConfigOpsProvisionSecret
from configops.config import get_config
from configops.utils.exception import ConfigOpsException
from configops.utils.constants import SystemType
from configops.utils.secret_util import encrypt_data

logger = logging.getLogger(__name__)

_ALREADY_EXISTS = "already exists"


class Code(Enum):
    OK = "OK"
    EXISTS = "EXISTS"
    ERROR = "ERROR"


class Result:
    def __init__(self, code: Code, msg: Optional[str] = None):
        self.code = code
        self.msg = msg if msg else ""

    def __str__(self):
        return f"[{self.code.name}] {self.msg}"

    def is_ok(self):
        return Code.OK == self.code or Code.EXISTS == self.code

    def is_exists(self):
        return Code.EXISTS == self.code


class Creator:

    def __init__(self, db_id: str, db_config):
        self.db_id = db_id
        self.db_config = db_config

    def __get_default_ok_result__(
        self, db_name: str, user: str, permissions
    ) -> tuple[Result, Result, Result]:
        create_db_result, create_user_result, grant_user_result = (
            Result(Code.OK, f"Create database [{db_name}] ok"),
            Result(
                Code.OK,
                f"Create user [{user}] ok, check the console for the key information.",
            ),
            Result(Code.OK, f"Grant user with {permissions} ok"),
        )
        return create_db_result, create_user_result, grant_user_result

    def create(
        self, db_name: str, user: str, pwd: str, **kwargs
    ) -> tuple[Optional[Result], Optional[Result], Optional[Result]]: ...


class MysqlCreator(Creator):

    def create(
        self, db_name: str, user: str, pwd: str, **kwargs
    ) -> tuple[Optional[Result], Optional[Result], Optional[Result]]:
        ip_range = kwargs.get("ipsource", "%")
        permissions = kwargs.get(
            "permissions", ["SELECT", "INSERT", "UPDATE", "DELETE"]
        )
        mysql_user = f"'{user}'@'{ip_range}'"
        engine = create_database_engine(self.db_config)

        create_db_result, create_user_result, grant_user_result = (
            self.__get_default_ok_result__(db_name, user, permissions)
        )

        with engine.connect() as conn:
            # 创建数据库
            try:
                conn.execute(sqlalchemy.text(f"CREATE DATABASE `{db_name}`;"))
            except DBAPIError as ex:
                err_message = str(ex.orig)
                if err_message.find("1007") >= 0:
                    logger.warning(f"Mysql create database warning. {ex}")
                    create_db_result = Result(
                        Code.EXISTS, f"Database [{db_name}] already exists"
                    )
                else:
                    logger.error(f"Mysql create database error. {ex}")
                    create_db_result = Result(Code.ERROR, err_message)
                    return create_db_result, None, None

            # 创建用户
            try:
                conn.execute(
                    sqlalchemy.text(f"CREATE USER {mysql_user} IDENTIFIED BY :pwd;"),
                    {"pwd": pwd},
                )
                store_secret(self.db_id, db_name, user, pwd)
            except DBAPIError as ex:
                err_message = str(ex.orig)
                if err_message.find("1396") >= 0:
                    logger.warning(f"Mysql create user warning. {ex}")
                    create_user_result = Result(
                        Code.EXISTS, f"User [{user}] already exists"
                    )
                else:
                    logger.error(f"Mysql create user error. {ex}")
                    create_user_result = Result(Code.ERROR, err_message)
                    return None, create_user_result, None

            # 授权
            try:
                conn.execute(
                    sqlalchemy.text(
                        f"GRANT {",".join(permissions)} ON `{db_name}`.* TO {mysql_user};"
                    )
                )
            except DBAPIError as ex:
                err_message = str(ex)
                logger.warning(f"Mysql grant user error. {ex}")
                grant_user_result = Result(Code.ERROR, err_message)
                return None, None, grant_user_result
        return create_db_result, create_user_result, grant_user_result


class PostgreCreator(Creator):

    def create(
        self, db_name: str, user: str, pwd: str, **kwargs
    ) -> tuple[Optional[Result], Optional[Result], Optional[Result]]:
        permissions = kwargs.get(
            "permissions", ["SELECT", "INSERT", "UPDATE", "DELETE"]
        )

        create_db_result, create_user_result, grant_user_result = (
            self.__get_default_ok_result__(db_name, user, permissions)
        )

        engine = create_database_engine(self.db_config)
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            try:
                conn.execute(sqlalchemy.text(f"CREATE DATABASE {db_name}"))
            except DBAPIError as ex:
                err_message = str(ex.orig)
                if _ALREADY_EXISTS in err_message:
                    logger.warning(f"Postgre create database warning: {ex}")
                    create_db_result = Result(
                        Code.EXISTS, f"Database [{db_name}] already exists"
                    )
                else:
                    create_db_result = Result(Code.ERROR, err_message)
                    return create_db_result, None, None

            try:
                conn.execute(
                    sqlalchemy.text(f"CREATE USER {user} WITH PASSWORD :pwd"),
                    {"pwd": pwd},
                )
                store_secret(self.db_id, db_name, user, pwd)
            except DBAPIError as ex:
                err_message = str(ex.orig)
                if _ALREADY_EXISTS in err_message:
                    logger.warning(f"Postgre create user warning: {ex}")
                    create_user_result = Result(
                        Code.EXISTS, f"User [{user}] already exists"
                    )
                else:
                    create_user_result = Result(Code.ERROR, err_message)
                    return None, create_user_result, None

        # 切换到db，授权
        engine = create_database_engine(
            self.db_config,
            db_name,
        )
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            try:
                conn.execute(
                    sqlalchemy.text(f"GRANT CONNECT ON DATABASE {db_name} TO {user}")
                )
                conn.execute(sqlalchemy.text(f"GRANT USAGE ON SCHEMA public TO {user}"))
                conn.execute(
                    sqlalchemy.text(
                        f"GRANT {",".join(permissions)} ON ALL TABLES IN SCHEMA public TO {user}"
                    )
                )
                conn.execute(
                    sqlalchemy.text(
                        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT {",".join(permissions)} ON TABLES TO {user}"
                    )
                )
            except DBAPIError as ex:
                err_message = str(ex.orig)
                logger.error(f"Postgre grant user error: {ex}")
                grant_user_result = Result(Code.ERROR, err_message)
                return None, None, grant_user_result

        return create_db_result, create_user_result, grant_user_result


def get_creator(db_id: str, db_config) -> Creator:
    dialect = db_config.get("dialect")
    if dialect == "mysql":
        return MysqlCreator(db_id, db_config)
    elif dialect == "postgresql":
        return PostgreCreator(db_id, db_config)
    else:
        raise ConfigOpsException(f"Unsupported dialect {dialect}")


def store_secret(db_id: str, db_name: str, user: str, pwd: str):
    _secret = get_config(current_app, "config.node.secret")
    if _secret:
        secret_key = base64.b64decode(_secret)
        encrypted_password = encrypt_data(pwd.encode(), secret_key)
        provision_secret = (
            db.session.query(ConfigOpsProvisionSecret)
            .filter_by(
                system_id=db_id, system_type=SystemType.DATABASE.value, username=user
            )
            .first()
        )
        if provision_secret:
            provision_secret.password = encrypted_password
        else:
            provision_secret = ConfigOpsProvisionSecret(
                system_id=db_id,
                system_type=SystemType.DATABASE.value,
                object=db_name,
                username=user,
                password=encrypted_password,
            )
            db.session.add(provision_secret)

        db.session.commit()
