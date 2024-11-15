""" 执行SQL操作 """

from flask import Blueprint, request, make_response, jsonify, current_app, Response
import re, logging, os, json, collections, subprocess, platform, string, random
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import create_engine, text
from marshmallow import Schema, fields, ValidationError, EXCLUDE
from configops.config import get_database_cfg, get_java_home_dir, get_liquibase_cfg
from configops.utils.constants import DIALECT_DRIVER_MAP, extract_version
from configops.utils import secret_util

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
    db_id = data.get("dbId")
    db_config = get_database_cfg(db_id)
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
    data = None
    try:
        schema = RunLiquibaseCmdSchema()
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400

    cmd_args_str = "liquibase " + data["command"]

    db_id = data.get("dbId")
    if db_id:
        db_config = get_database_cfg(db_id)
        if db_config == None:
            return make_response("Database not found", 404)

        dialect = db_config.get("dialect", "mysql")
        host = db_config["url"]
        port = db_config["port"]
        username = db_config["username"]

        secret_data = secret_util.get_secret_data(db_config)
        password = secret_data.password

        # jdbc:database_type://hostname:port/database_name
        cmd_args_str = (
            cmd_args_str
            + f" --url jdbc:{dialect}://{host}:{port} --username {username} --password {password}"
        )
        changelogSchema = db_config.get("changelogschema", "liquibase")
        cmd_args_str = cmd_args_str + f" --liquibase-schema-name {changelogSchema}"

    if data.get("args"):
        cmd_args_str = cmd_args_str + " " + data.get("args")

    # 设置classpath 和 defaultsFile
    liquibase_cfg = get_liquibase_cfg(current_app)
    if liquibase_cfg:
        defaultsFile = liquibase_cfg.get("defaults-file")
        jdbcDriverDir = liquibase_cfg.get("jdbc-drivers-dir")
        defaultsFileOpt = (
            cmd_args_str.find("--defaults-file") < 0
            or cmd_args_str.find("--defaultsFile") < 0
        )
        classpathOpt = cmd_args_str.find("--classpath") < 0

        if defaultsFile and os.path.exists(defaultsFile) and defaultsFileOpt:
            cmd_args_str = (
                cmd_args_str + " --defaults-file " + os.path.abspath(defaultsFile)
            )

        if jdbcDriverDir and os.path.exists(jdbcDriverDir) and classpathOpt:
            separator = ";" if platform.system() == "Windows" else ":"
            base = os.path.abspath(jdbcDriverDir)

            jar_files = [f for f in os.listdir(jdbcDriverDir) if f.endswith(".jar")]

            classpath = separator.join(os.path.join(base, jar) for jar in jar_files)

            cmd_args_str = cmd_args_str + " --classpath " + classpath

    # 解析changelogFile
    tmpChangelogRoot = None
    changelogFile = data.get("changeLogFile")
    if changelogFile:
        if not os.path.exists(changelogFile):
            return make_response(
                f"error: changeLogFile {changelogFile} not found ", 400
            )

        if os.path.isdir(changelogFile):
            # 文件夹下面的changelog文件，聚合成一个change-root.yaml
            changelogfiles = []
            for _, _, filenames in os.walk(changelogFile):
                for filename in filenames:
                    if filename.endswith((".yaml", ".yml", ".xml")):
                        changelogfiles.append(filename)
            changelogfiles = sorted(changelogfiles, key=extract_version)

            if len(changelogfiles) > 0:
                suffix = "".join(
                    random.sample(string.ascii_lowercase + string.digits, 10)
                )
                rootFileName = f"changelog_root_{suffix}.yaml"
                rootFileContent = "databaseChangeLog:"
                for file in changelogfiles:
                    rootFileContent = (
                        rootFileContent + f"\n  - include:\n      file: {file}"
                    )
                tmpChangelogRoot = os.path.join(changelogFile, rootFileName)
                with open(tmpChangelogRoot, "w", encoding="utf-8") as file:
                    file.write(rootFileContent)

                cmd_args_str = cmd_args_str + " --changelog-file " + rootFileName

        elif os.path.isfile(changelogFile):
            cmd_args_str = cmd_args_str + " --changelog-file " + changelogFile

    logger.info(f"Liquibase command: {cmd_args_str}")
    args = re.split(r"\s+", cmd_args_str.strip())

    try:
        custom_env = os.environ.copy()
        # 设置JavaHome
        java_home = get_java_home_dir(current_app)
        if java_home:
            custom_env["JAVA_HOME"] = java_home

        working_dir = os.getcwd()
        if data.get("cwd"):
            working_dir = data.get("cwd")

        completed_process = subprocess.run(
            args,
            cwd=working_dir,
            capture_output=True,
            env=custom_env,
        )
        stdout = completed_process.stdout.decode()
        stderr = completed_process.stderr.decode()
        if stderr:
            logger.info(f"Liqubase run stderr. \n{stderr}")
        if stdout:
            logger.info(f"Liqubase run stdout. \n{stdout}")
        return {
            "stdout": stdout,
            "stderr": stderr,
            "retcode": completed_process.returncode,
        }
    finally:
        # 临时文件删除掉
        if tmpChangelogRoot:
            os.remove(tmpChangelogRoot)
