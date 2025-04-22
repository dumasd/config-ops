# -*- coding: utf-8 -*-
# @Author  : Bruce Wu
from flask import Blueprint, request, make_response, jsonify, current_app, Response
import re, logging, os, json, collections, subprocess, platform, string, random, shlex
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import create_engine, text
from marshmallow import Schema, fields, EXCLUDE
from configops.config import get_database_cfg, get_java_home_dir, get_liquibase_cfg
from configops.utils.constants import DIALECT_DRIVER_MAP, extract_version
from configops.utils import secret_util
from configops.utils.exception import ConfigOpsException
from configops.database.utils import create_database_engine
from configops.changelog.database_change import DatabaseChangeLog

logger = logging.getLogger(__name__)

bp = Blueprint(
    "database", __name__, url_prefix=os.getenv("FLASK_APPLICATION_ROOT", "/")
)


class DatabaseJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(obj, date):
            return obj.strftime("%Y-%m-%d")
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, Enum):
            return obj.name
        elif isinstance(obj, bytes):
            return str(obj, encoding="utf-8")
        else:
            return json.JSONEncoder.default(self, obj)


class RunSqlSchema(Schema):
    dbId = fields.Str(required=True)
    sql = fields.Str(required=True)
    database = fields.Str(required=False)

    class Meta:
        unknown = EXCLUDE


class RunLiquibaseCmdSchema(Schema):
    dbId = fields.Str(required=False)
    command = fields.Str(required=True)
    args = fields.Str(required=False)
    changeLogFile = fields.Str(required=False)
    # 命令运行在哪个目录下
    cwd = fields.Str(required=False)

    class Meta:
        unknown = EXCLUDE


def __remove_comments__(sql_script):
    sql_script = re.sub(r"--.*?\n", "", sql_script)
    sql_script = re.sub(r"/\*.*?\*/", "", sql_script, flags=re.DOTALL)
    return sql_script


def execute_sql(database, sql_script, db_config):
    sql_commands = None
    engine = None
    try:
        engine = create_database_engine(db_config, database)
        sql_script = __remove_comments__(sql_script)
        sql_commands = sql_script.split(";")
    except Exception as e:
        logger.error(f"Init database or sql error. {e}")
        return False, f"Init database or sql error: {str(e)}"

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            execute_res = []
            for sql in sql_commands:
                if not sql.strip():
                    continue
                sql_text = text(sql.strip())
                logger.info(f"============ 执行SQL语句 =========\n {sql_text}")
                result = conn.execute(sql_text)
                rows = []
                if result.returns_rows:
                    columes = result.keys()
                    for row in result:
                        rowDict = collections.OrderedDict()
                        index = 0
                        for colume in columes:
                            rowDict[colume] = row[index]
                            index += 1
                        rows.append(rowDict)
                execute_res.append(
                    {
                        "sql": f"{sql_text}",
                        "rowcount": result.rowcount,
                        "rows": rows,
                    }
                )
            trans.commit()
            return True, execute_res
        except Exception as ex:
            trans.rollback()
            logger.error(f"Execute sql error {ex}")
            return False, f"Execute sql error {ex}"
        finally:
            trans.close()


@bp.route("/database/v1/list", methods=["GET"])
def get_database_list():
    configs = current_app.config["database"]
    db_cfgs = []
    for k in configs:
        db_cfgs.append({"db_id": k})
    return db_cfgs


@bp.route("/database/v1/run-sql", methods=["PUT"])
def run_sql():
    data = RunSqlSchema().load(request.get_json())
    db_id = data.get("dbId")
    db_config = get_database_cfg(current_app, db_id)
    if db_config == None:
        return make_response("Database config not found", 404)
    success, result = execute_sql(data.get("database"), data.get("sql"), db_config)
    if not success:
        return result, 400
    resp = collections.OrderedDict()
    resp["database"] = db_config.get("url")
    resp["result"] = result
    resp_json = json.dumps(resp, cls=DatabaseJsonEncoder)
    jsonify()
    return Response(resp_json, mimetype="application/json")


@bp.route("/database/v1/run-liquibase", methods=["POST"])
def run_liquibase():
    """
    执行liquibase命令
    """
    data = RunLiquibaseCmdSchema().load(request.get_json())
    change_log = DatabaseChangeLog(data.get("changeLogFile"), current_app)
    return change_log.run_liquibase_cmd(
        data["command"], data.get("cwd"), data.get("args"), data.get("dbId")
    )
