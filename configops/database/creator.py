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
from configops.utils.secret_util import encrypt_data, decrypt_data

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

    def is_success(self):
        return self.is_ok() or self.is_exists()

    def is_ok(self):
        return Code.OK == self.code

    def is_exists(self):
        return Code.EXISTS == self.code


class Creator:

    def __init__(self, db_id: str, db_config):
        self.db_id = db_id
        self.db_config = db_config
        self.engine = create_database_engine(db_config)

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

    def create_database(self, db_name: str, **kwargs) -> Result:
        raise NotImplementedError("create_database not implemented by subclasses")

    def create_user(self, user: str, pwd: str, **kwargs) -> Result:
        raise NotImplementedError("create_user not implemented by subclasses")

    def grant_user(self, user: str, db_name: str, **kwargs) -> Result:
        raise NotImplementedError("grant_user not implemented by subclasses")


class MysqlCreator(Creator):

    def create_database(self, db_name, **kwargs) -> Result:
        result = Result(Code.OK, f"Create database [{db_name}] ok")
        with self.engine.connect() as conn:
            try:
                conn.execute(sqlalchemy.text(f"CREATE DATABASE `{db_name}`;"))
            except DBAPIError as ex:
                err_message = str(ex.orig)
                if err_message.find("1007") >= 0:
                    logger.warning(f"Mysql create database warning. {ex}")
                    result = Result(Code.EXISTS, f"Database [{db_name}] already exists")
                else:
                    logger.error(f"Mysql create database error. {ex}")
                    result = Result(Code.ERROR, err_message)
        return result

    def create_user(self, user: str, pwd: str, **kwargs) -> Result:
        ip_range = kwargs.get("ipsource", "%")
        mysql_user = f"'{user}'@'{ip_range}'"
        result = Result(
            Code.OK,
            f"Create user [{user}] ok, check the console for the key information.",
        )
        with self.engine.connect() as conn:
            try:
                conn.execute(
                    sqlalchemy.text(f"CREATE USER {mysql_user} IDENTIFIED BY :pwd;"),
                    {"pwd": pwd},
                )
            except DBAPIError as ex:
                err_message = str(ex.orig)
                if err_message.find("1396") >= 0:
                    logger.warning(f"Mysql create user warning. {ex}")
                    result = Result(Code.EXISTS, f"User [{user}] already exists")
                else:
                    logger.error(f"Mysql create user error. {ex}")
                    result = Result(Code.ERROR, err_message)
        return result

    def grant_user(self, user: str, db_name: str, **kwargs) -> Result:
        ip_range = kwargs.get("ipsource", "%")
        permissions = kwargs.get(
            "permissions", ["SELECT", "INSERT", "UPDATE", "DELETE"]
        )
        mysql_user = f"'{user}'@'{ip_range}'"
        result = Result(Code.OK, f"Grant user with {permissions} ok")
        permissions_text = ",".join(permissions)
        with self.engine.connect() as conn:
            try:
                conn.execute(
                    sqlalchemy.text(
                        f"GRANT {permissions_text} ON `{db_name}`.* TO {mysql_user};"
                    )
                )
            except DBAPIError as ex:
                err_message = str(ex)
                logger.warning(f"Mysql grant user error. {ex}")
                result = Result(Code.ERROR, err_message)
        return result


class PostgreCreator(Creator):
    def create_database(self, db_name: str, **kwargs) -> Result:
        result = Result(Code.OK, f"Create database [{db_name}] ok")
        with self.engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as conn:
            try:
                conn.execute(sqlalchemy.text(f"CREATE DATABASE {db_name}"))
            except DBAPIError as ex:
                err_message = str(ex.orig)
                if _ALREADY_EXISTS in err_message:
                    logger.warning(f"Postgre create database warning: {ex}")
                    result = Result(Code.EXISTS, f"Database [{db_name}] already exists")
                else:
                    result = Result(Code.ERROR, err_message)
        return result

    def create_user(self, user: str, pwd: str, **kwargs) -> Result:
        result = Result(
            Code.OK,
            f"Create user [{user}] ok, check the console for the key information.",
        )
        with self.engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as conn:
            try:
                conn.execute(
                    sqlalchemy.text(f"CREATE USER {user} WITH PASSWORD :pwd"),
                    {"pwd": pwd},
                )
            except DBAPIError as ex:
                err_message = str(ex.orig)
                if _ALREADY_EXISTS in err_message:
                    logger.warning(f"Postgre create user warning: {ex}")
                    result = Result(Code.EXISTS, f"User [{user}] already exists")
                else:
                    result = Result(Code.ERROR, err_message)
        return result

    def grant_user(self, user: str, db_name: str, **kwargs) -> Result:
        permissions = kwargs.get(
            "permissions", ["SELECT", "INSERT", "UPDATE", "DELETE"]
        )
        permissions_text = ",".join(permissions)
        grant_engine = create_database_engine(
            self.db_config,
            db_name,
        )
        result = Result(Code.OK, f"Grant user with {permissions} ok")
        with grant_engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as conn:
            try:
                conn.execute(
                    sqlalchemy.text(f"GRANT CONNECT ON DATABASE {db_name} TO {user}")
                )
                conn.execute(sqlalchemy.text(f"GRANT USAGE ON SCHEMA public TO {user}"))
                conn.execute(
                    sqlalchemy.text(
                        f"GRANT {permissions_text} ON ALL TABLES IN SCHEMA public TO {user}"
                    )
                )
                conn.execute(
                    sqlalchemy.text(
                        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT {permissions_text} ON TABLES TO {user}"
                    )
                )
            except DBAPIError as ex:
                err_message = str(ex.orig)
                logger.error(f"Postgre grant user error: {ex}")
                result = Result(Code.ERROR, err_message)
        return result


def get_creator(db_id: str, db_config) -> Creator:
    dialect = db_config.get("dialect")
    if dialect == "mysql":
        return MysqlCreator(db_id, db_config)
    elif dialect == "postgresql":
        return PostgreCreator(db_id, db_config)
    else:
        raise ConfigOpsException(f"Unsupported dialect {dialect}")


def store_secret(db_id: str, user: str, pwd: str):
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
                object="",
                username=user,
                password=encrypted_password,
            )
            db.session.add(provision_secret)
        db.session.commit()


def update_db(db_id: str, db_name: str, user: str) -> Optional[str]:
    _secret = get_config(current_app, "config.node.secret")
    if not _secret:
        return None

    provision_secret = (
        db.session.query(ConfigOpsProvisionSecret)
        .filter_by(
            system_id=db_id, system_type=SystemType.DATABASE.value, username=user
        )
        .first()
    )
    if provision_secret:
        if provision_secret.object:
            db_names = provision_secret.object.split(",")
            if db_name not in db_names:
                db_names.append(db_name)
            provision_secret.object = ",".join(db_names)
        else:
            provision_secret.object = db_name
        db.session.commit()
        secret_key = base64.b64decode(_secret)
        raw_password = decrypt_data(provision_secret.password, secret_key).decode()
        return raw_password
    return None
