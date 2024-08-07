from ops.utils import parser, constants
from ops.api import database
import logging

logger = logging.getLogger(__name__)

def test_validate_sql():
    sql_script = """
    SELECT * FROM elespacio_rd_kpi;
    -- 注释
    UPDATE sales SET larbor_cost=10 WHERE id = 3;
    -- comment
    CREATE TABLE `area` (
    `id` varchar(255) NOT NULL COMMENT '区域id,和文件对应',
    `level` varchar(255) DEFAULT NULL COMMENT '区域级别，从高到低country,province,city,district,更细的待定',
    `name` varchar(255) DEFAULT NULL COMMENT '区域名称',
    `pid` varchar(255) NOT NULL COMMENT '父级区域id',
    PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='地图区域表' ;
    """
    db_config = {'url': 'mysql+mysqlconnector://root:1234@localhost/test'}
    database.validate_sql(sql_script, db_config)

def test_execute_sql():
    sql_script = """
    SELECT * FROM elespacio_rd_kpi;
    -- 注释
    UPDATE sales SET labor_cost=10 WHERE1 id = 3;
    -- comment
    CREATE TABLE IF NOT EXISTS `area` (
    `id` varchar(255) NOT NULL COMMENT '区域id,和文件对应',
    `level` varchar(255) DEFAULT NULL COMMENT '区域级别，从高到低country,province,city,district,更细的待定',
    `name` varchar(255) DEFAULT NULL COMMENT '区域名称',
    `pid` varchar(255) NOT NULL COMMENT '父级区域id',
    PRIMARY KEY (`id`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='地图区域表' ;
    """    
    db_config = {'url': 'mysql+mysqlconnector://root:1234@localhost/test'}
    database.execute_sql(sql_script, db_config)