import io
import logging
from configops.database.creator import MysqlCreator, PostgreCreator

logger = logging.getLogger(__name__)


class TestMysqlCreator:
    def test_create(self):
        db_config = {
            "dialect": "mysql",
            "url": "localhost",
            "port": 3306,
            "username": "root",
            "password": "12345678",
        }
        mysqlCreator = MysqlCreator("db1", db_config)
        db, user, grant = mysqlCreator.create(
            db_name="dev_2", user="dev_2", pwd="1234@Ass", ipsource="%"
        )
        logger.info(f"Mysql create result: {db}, {user}, {grant}")


class TestPostgreCreator:
    def test_create(self):
        db_config = {
            "dialect": "postgresql",
            "url": "localhost",
            "port": 5432,
            "username": "wukai",
            "password": "1234",
        }
        postgreCreator = PostgreCreator("db2", db_config)
        db, user, grant = postgreCreator.create(
            db_name="gtt_videomart_meta", user="gtt_videomart_meta", pwd="123456@Aa"
        )
        logger.info(f"Postgre create result: {db}, {user}, {grant}")
