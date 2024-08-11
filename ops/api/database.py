""" 执行SQL操作 """

from flask import Blueprint, request, make_response, jsonify, current_app
import re, logging
from sqlalchemy import create_engine, text
from marshmallow import Schema, fields, ValidationError

logger = logging.getLogger(__name__)

bp = Blueprint("database", __name__)


class DbConfig(Schema):
    url = fields.Str(required=True, default="localhost")
    port = fields.Integer(required=True, default=3306)
    username = fields.Str(required=True)
    password = fields.Str(required=True)
    database = fields.Str(required=True)


class RunSqlSchema(Schema):
    db_id = fields.Str(required=True)
    sql = fields.Str(required=True)


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


def execute_sql(sql_script, db_config):
    engine = None
    sql_commands = None
    try:
        url = db_config.get("url")
        username = db_config.get("username")
        password = db_config.get("password")
        port = db_config.get("port")
        database = db_config.get("database")
        conn_string = (
            f"mysql+mysqlconnector://{username}:{password}@{url}:{port}/{database}"
        )
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
                    sql_text = text(sql)
                    logger.info(f"============ 执行SQL语句 =========\n {sql_text}")
                    result = conn.execute(sql_text)
                    execute_res.append(
                        {"sql": f"{sql_text}", "rowcount": result.rowcount}
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
    success, result = execute_sql(data.get("sql"), db_config)
    if not success:
        return result, 400
    print(result)
    return {"database": db_config.get("url"), "result": result}
