# -*- coding: utf-8 -*-
# @Author  : Bruce Wu
"""
This Python file contains functionality for [briefly describe the purpose of the file].
It is designed to [explain what the file does or its main use case].
"""

from flask import Blueprint, jsonify, make_response, request, current_app, session
import logging, asyncio, threading, os
from marshmallow import Schema, fields, EXCLUDE
from configops.utils.constants import PermissionModule
from configops.database.db import db, ManagedObjects, Worker, GroupPermission
from configops.api.utils import BaseResult, auth_required, do_check_auth
from marshmallow import Schema, fields, EXCLUDE
from configops.utils.constants import CONTROLLER_NAMESPACE, X_WORKSPACE
from configops.cluster.messages import Message, MessageType
import sqlalchemy

bp = Blueprint(
    "workplace", __name__, url_prefix=os.getenv("FLASK_APPLICATION_ROOT", "/")
)

logger = logging.getLogger(__name__)


class ApiDeleteChangelogSchema(Schema):
    change_set_id = fields.Str(required=True)
    system_id = fields.Str(required=True)
    system_type = fields.Str(required=True)

    class Meta:
        unknown = EXCLUDE


class CallbackFuture(asyncio.Future):
    def __init__(self, event=None, loop=None):
        super().__init__(loop=loop)
        self.event = event

    def set_result(self, result):
        super().set_result(result)
        if self.event:
            self.event.set()

    def set_exception(self, ex):
        super().set_exception(ex)
        if self.event:
            self.event.set()


@bp.route("/api/dashboard/managed_objects/v1", methods=["GET"])
@auth_required()
def list_managed_objects():
    workerspace_id = request.headers[X_WORKSPACE]
    groups = session["groups"]
    stmt = (
        sqlalchemy.select(
            ManagedObjects.id,
            ManagedObjects.system_id,
            ManagedObjects.system_type,
            ManagedObjects.url,
            ManagedObjects.worker_id,
            Worker.name.label("worker_name"),
        )
        .join(GroupPermission, ManagedObjects.id == GroupPermission.source_id)
        .join(Worker, ManagedObjects.worker_id == Worker.id)
        .where(
            Worker.workspace_id == workerspace_id, GroupPermission.group_id.in_(groups)
        )
    )
    items = db.session.execute(stmt).all()
    data = [
        {
            "id": item.id,
            "system_id": item.system_id,
            "system_type": item.system_type,
            "url": item.url,
            "worker_id": item.worker_id,
            "worker_name": item.worker_name,
        }
        for item in items
    ]
    return BaseResult(data=data).response()


@bp.route("/api/dashboard/changelogs/v1", methods=["GET"])
async def get_changelogs():
    check_auth_resp = do_check_auth(
        module=PermissionModule.MANAGED_OBJECT_CHANGELOG_MANAGE, actions=["READ"]
    )
    if check_auth_resp:
        return check_auth_resp

    managed_object_id = request.args["managed_object_id"]
    managed_object = (
        db.session.query(ManagedObjects)
        .filter(ManagedObjects.id == managed_object_id)
        .first()
    )

    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 10))
    q = request.args.get("q", "")
    start_time = request.args.get("start_time", "")
    end_time = request.args.get("end_time", "")
    message = Message(
        type=MessageType.QUERY_CHANGE_LOG,
        data={
            "page": page,
            "size": size,
            "q": q,
            "start_time": start_time,
            "end_time": end_time,
            "system_id": managed_object.system_id,
            "system_type": managed_object.system_type,
        },
    )
    event = threading.Event()
    future = CallbackFuture(event)

    controller_namespace = current_app.config.get(CONTROLLER_NAMESPACE)
    controller_namespace.send_message(managed_object.worker_id, message, future)
    if event.wait(5):
        result = future.result()
        if result:
            return result
        else:
            raise future.exception()
    else:
        # 超时了
        return BaseResult(data=[]).response(0)


@bp.route("/api/dashboard/changelogs/v1", methods=["DELETE"])
async def delete_changelogs():
    check_auth_resp = do_check_auth(
        module=PermissionModule.MANAGED_OBJECT_CHANGELOG_MANAGE, actions=["READ"]
    )
    if check_auth_resp:
        return check_auth_resp

    managed_object_id = request.args["managed_object_id"]

    managed_object = (
        db.session.query(ManagedObjects)
        .filter(ManagedObjects.id == managed_object_id)
        .first()
    )

    changelogs = request.get_json()
    if len(changelogs) <= 0:
        return BaseResult().response()

    change_set_ids = []
    for item in changelogs:
        ApiDeleteChangelogSchema().load(item)
        if (
            item["system_id"] != managed_object.system_id
            or item["system_type"] != managed_object.system_type
        ):
            return make_response("Illegal paramaters", 400)
        change_set_ids.append(item["change_set_id"])

    message = Message(
        type=MessageType.DELETE_CHANGE_LOG,
        data={
            "system_id": managed_object.system_id,
            "system_type": managed_object.system_type,
            "change_set_ids": change_set_ids,
        },
    )

    event = threading.Event()
    controller_ns = current_app.config.get(CONTROLLER_NAMESPACE)
    future = CallbackFuture(event)
    controller_ns.send_message(managed_object.worker_id, message, future)

    if event.wait(5):
        result = future.result()
        if result:
            return result
        else:
            raise future.exception()
    else:
        return BaseResult.error(
            "Deletion timed out. Please refresh the data or try again."
        ).response()
