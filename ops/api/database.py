""" 执行SQL操作 """

from flask import Blueprint, request, make_response, jsonify, current_app, Response
import re, logging
import collections
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import json
import base64
from sqlalchemy import create_engine, text
from marshmallow import Schema, fields, ValidationError
from ops.config import DbConfig
from ops.utils.constants import DIALECT_DRIVER_MAP


logger = logging.getLogger(__name__)

bp = Blueprint("database", __name__)


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
            # return base64.b64encode(obj).decode("utf-8")
        else:
            return json.JSONEncoder.default(self, obj)


class RunSqlSchema(Schema):
    db_id = fields.Str(required=True)
    sql = fields.Str(required=True)
    database = fields.Str(required=False)


def remove_comments(sql_script):
    sql_script = re.sub(r"--.*?\n", "", sql_script)
    sql_script = re.sub(r"/\*.*?\*/", "", sql_script, flags=re.DOTALL)
    return sql_script


def validate_sql(sql_script: str, db_config):
    try:
        url = db_config.get("url")
        engine = create_engine(url)
        sql_script = remove_comments(sql_script)
        sql_commands = sql_script.split(";")
        for sql in sql_commands:
            if sql.strip():
                sql_text = text(sql)
                compiled = sql_text.compile(engine)
                logger.info(compiled)
    except Exception as e:
        return False, f"Invalid SQL statement: {str(e)}"


def execute_sql(database, sql_script, db_config):
    engine = None
    sql_commands = None
    try:
        url = db_config.get("url")
        username = db_config.get("username")
        password = db_config.get("password")
        port = db_config.get("port")
        dialect = db_config.get("dialect")
        driver = DIALECT_DRIVER_MAP.get(dialect)
        if driver is None:
            raise Exception(f"Unsupported dialect {dialect}")

        conn_string = f"{dialect}+{driver}://{username}:{password}@{url}:{port}"
        if database is not None and len(database.strip()) > 0:
            conn_string = conn_string + f"/{database}"
        engine = create_engine(conn_string)
        sql_script = remove_comments(sql_script)
        sql_commands = sql_script.split(";")
    except Exception as e:
        logger.error(f"Init database or sql error. {e}")
        return False, f"Init database or sql error: {str(e)}"

    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # 执行结果包装一下
            execute_res = []
            for sql in sql_commands:
                if sql.strip():
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


def get_database_config(db_id):
    configs = current_app.config["database"]
    db_config = configs[db_id]
    if db_config == None:
        return None
    schema = DbConfig()
    return schema.load(db_config)


@bp.route("/database/v1/list", methods=["GET"])
def get_database_list():
    configs = current_app.config["database"]
    list = []
    for k in configs:
        list.append({"db_id": k})
    return list


@bp.route("/database/v1/run-sql", methods=["PUT"])
def run_sql():
    schema = RunSqlSchema()
    data = None
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400
    db_id = data.get("db_id")
    db_config = get_database_config(db_id)
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
