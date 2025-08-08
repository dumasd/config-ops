# -*- coding: utf-8 -*-
# @Author  : Bruce Wu
from flask import Blueprint, request, make_response, current_app
import logging, os, json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from marshmallow import Schema, fields, EXCLUDE
from configops.config import get_database_cfg
from configops.changelog.database_change import DatabaseChangeLog
from configops.database import creator as db_creator
from configops.utils import secret_util

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


class RunLiquibaseCmdSchema(Schema):
    dbId = fields.Str(required=False)
    command = fields.Str(required=True)
    args = fields.Str(required=False)
    changeLogFile = fields.Str(required=False)
    # 命令运行在哪个目录下
    cwd = fields.Str(required=False)

    class Meta:
        unknown = EXCLUDE


class ProvisionDbUserSchema(Schema):
    dbId = fields.Str(required=True)
    dbName = fields.Str(required=True)
    user = fields.Str(required=True)
    ipsource = fields.Str(required=True)
    permissions = fields.List(fields.Str, required=False)

    class Meta:
        unknown = EXCLUDE


@bp.route("/database/v1/list", methods=["GET"])
def get_database_list():
    configs = current_app.config["database"]
    db_cfgs = []
    for k in configs:
        db_cfgs.append({"db_id": k})
    return db_cfgs


@bp.route("/database/v1/provision", methods=["POST"])
def provision():
    data = ProvisionDbUserSchema().load(request.get_json())
    db_id = data.get("dbId")
    user = data.get("user")
    db_name = data.get("dbName")
    ipsource = data.get("ipsource", "%")
    permissions = data.get("permissions", ["SELECT", "INSERT", "UPDATE", "DELETE"])
    db_config = get_database_cfg(current_app, db_id)
    if db_config == None:
        return make_response("Database config not found", 400)

    resp = {"messages": []}

    c = db_creator.get_creator(db_id, db_config)
    create_database_result = c.create_database(db_name)
    resp["messages"].append(create_database_result.msg)
    if not create_database_result.is_success():
        return resp, 500

    pwd = secret_util.generate_password(length=16, contain_special=True)
    create_user_result = c.create_user(user, pwd, ipsource=ipsource)
    resp["messages"].append(create_user_result.msg)
    if not create_user_result.is_success():
        return resp, 500

    if create_user_result.is_ok():
        db_creator.store_secret(db_id, user, pwd)

    grant_user_result = c.grant_user(
        user, db_name, permissions=permissions, ipsource=ipsource
    )
    resp["messages"].append(grant_user_result.msg)
    if not grant_user_result.is_success():
        return resp, 500

    db_password = db_creator.update_db(db_id, db_name, user)
    resp["password"] = db_password
    return resp


@bp.route("/database/v1/run-liquibase", methods=["POST"])
def run_liquibase():
    data = RunLiquibaseCmdSchema().load(request.get_json())
    change_log = DatabaseChangeLog(data.get("changeLogFile"), current_app)
    return change_log.run_liquibase_cmd(
        data["command"], data.get("cwd"), data.get("args"), data.get("dbId")
    )
