from configops.utils.exception import ConfigOpsException
import sqlalchemy
import logging
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

_DIALECT_DRIVER_MAP = {
    "mysql": "mysqlconnector",
    "postgresql": "psycopg2",
}

def create_database_engine(db_config, schema: str = None) -> sqlalchemy.Engine:
    dialect = db_config.get("dialect")
    driver = _DIALECT_DRIVER_MAP.get(dialect)
    if driver is None:
        raise ConfigOpsException(f"Unsupported dialect {dialect}")
    url = db_config.get("url")
    username = db_config.get("username")
    password = db_config.get("password")
    port = db_config.get("port")
    schema_part = f"/{schema}" if schema else ""
    try:
        encoded_password = quote_plus(password)
        conn_string = f"{dialect}+{driver}://{username}:{encoded_password}@{url}:{port}{schema_part}"
        return sqlalchemy.create_engine(conn_string)
    except Exception as e:
        logger.error(f"Init database or sql error. {e}")
        raise e
