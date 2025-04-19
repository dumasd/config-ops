from configops.utils.constants import DIALECT_DRIVER_MAP
from configops.utils.exception import ConfigOpsException
import sqlalchemy
import logging
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


def create_database_engine(db_config):
    url = db_config.get("url")
    username = db_config.get("username")
    password = db_config.get("password")
    port = db_config.get("port")
    dialect = db_config.get("dialect")
    driver = DIALECT_DRIVER_MAP.get(dialect)
    schema = db_config.get("changelogschema", "liquibase")
    if driver is None:
        raise ConfigOpsException(f"Unsupported dialect {dialect}")
    try:
        encoded_password = quote_plus(password)
        conn_string = (
            f"{dialect}+{driver}://{username}:{encoded_password}@{url}:{port}/{schema}"
        )
        return sqlalchemy.create_engine(conn_string)
    except Exception as e:
        logger.error(f"Init database or sql error. {e}")
        raise e
