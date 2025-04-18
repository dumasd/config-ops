from flask import Blueprint, jsonify, make_response, request, current_app
import logging, sys, secrets
from marshmallow import Schema, fields, EXCLUDE
from configops.utils import constants
from configops.utils.constants import PermissionModule, PermissionType
from configops.database.db import (
    db,
    Workspace,
    Worker,
    ManagedObjects,
    GroupPermission,
    Group,
    paginate,
)
from configops.api.utils import BaseResult, auth_required
from marshmallow import Schema, fields, EXCLUDE, validate
from configops.utils.constants import CONTROLLER_NAMESPACE
import sqlalchemy

bp = Blueprint("admin", __name__)

logger = logging.getLogger(__name__)


class ApiWorkspaceSchema(Schema):
    id = fields.Str(required=False)
    name = fields.Str(required=True)
    description = fields.Str(required=False)

    class Meta:
        unknown = EXCLUDE


class ApiWorkerSchema(Schema):
    id = fields.Str(required=True)
    name = fields.Str(required=True)
    workspace_id = fields.Str(required=True)
    secret = fields.Str(required=False)

    class Meta:
        unknown = EXCLUDE


class ApiPermissionSchema(Schema):
    source_id = fields.Str(required=True)
    type = fields.Str(
        required=True, validate=validate.OneOf([e.name for e in PermissionModule])
    )
    permission = fields.Str(required=True)

    class Meta:
        unknown = EXCLUDE


class ApiGroupSchema(Schema):
    id = fields.Str(required=True)
    name = fields.Str(required=True)
    description = fields.Str(required=False)
    menus = fields.List(fields.Str(required=True), required=True)

    class Meta:
        unknown = EXCLUDE


class ApiWorkspacePermissionSchema(Schema):

    class ApiWorkspaceGroupPermissionSchema(ApiPermissionSchema):
        group_id = fields.Str(required=True)
        permissions = fields.List(fields.Str(required=True), required=True)

    id = fields.Str(required=True)
    group_permissions = fields.List(
        fields.Nested(ApiWorkspaceGroupPermissionSchema), required=True
    )

    class Meta:
        unknown = EXCLUDE


@bp.route(rule="/api/admin/group/v1", methods=["GET"])
@auth_required(module=PermissionModule.GROUP_MANAGE.name, actions=["READ"])
def read_group():
    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 10))
    q = request.args.get("q")

    query = db.session.query(Group)
    if q:
        query = query.filter(Group.id.like(f"%{q}%") | Group.name.like(f"%{q}%"))

    total = query.count()
    groups = query.limit(size).offset((page - 1) * size).all()

    return BaseResult(data=[item.to_dict() for item in groups]).response(total)


@bp.route(rule="/api/admin/group/v1", methods=["POST"])
@auth_required(module=PermissionModule.GROUP_MANAGE.name, actions=["CREATE"])
def create_group():
    data = ApiGroupSchema().load(request.get_json())
    group_id = data["id"]
    group = db.session.query(Group).filter(Group.id == group_id).first()
    if group:
        return make_response(f"Group id already exists {group_id}", 400)

    db.session.add(
        Group(id=group_id, name=data["name"], description=data.get("description", ""))
    )
    menus = data.get("menus", [])
    group_permissions = [
        GroupPermission(
            group_id=group_id,
            source_id=menu,
            permission=menu,
            type=PermissionType.WEB_MENU.name,
        )
        for menu in menus
    ]
    if len(group_permissions) > 0:
        db.session.add_all(group_permissions)
    db.session.commit()
    return BaseResult().response()


@bp.route(rule="/api/admin/group/menus/v1", methods=["GET"])
@auth_required(module=PermissionModule.GROUP_MANAGE.name, actions=["READ"])
def read_group_menus():
    group_id = request.args["id"]
    group = db.session.query(Group).filter(Group.id == group_id).first()
    menus = []
    if group:
        group_permissions = (
            db.session.query(GroupPermission)
            .filter(
                GroupPermission.group_id == group_id,
                GroupPermission.type == PermissionType.WEB_MENU.name,
            )
            .all()
        )
        menus = [item.permission for item in group_permissions]
    return BaseResult(data=menus).response()


@bp.route(rule="/api/admin/group/v1", methods=["PUT"])
@auth_required(module=PermissionModule.GROUP_MANAGE.name, actions=["EDIT"])
def edit_group():
    data = ApiGroupSchema().load(request.get_json())
    group_id = data["id"]
    group = db.session.query(Group).filter(Group.id == group_id).first()
    if group:
        group.name = data["name"]
        group.description = data.get("description", "")

        db.session.query(GroupPermission).filter(
            GroupPermission.group_id == group.id,
            GroupPermission.type == constants.PermissionType.WEB_MENU.name,
        ).delete()
        menus = data.get("menus")
        group_permissions = [
            GroupPermission(
                group_id=group_id,
                source_id=menu,
                permission=menu,
                type=PermissionType.WEB_MENU.name,
            )
            for menu in menus
        ]
        if len(group_permissions) > 0:
            db.session.add_all(group_permissions)
        db.session.commit()

    return BaseResult().response()


@bp.route(rule="/api/admin/workspace/v1", methods=["GET"])
@auth_required(module=PermissionModule.WORKSPACE_MANAGE.name, actions=["READ"])
def read_workspace():
    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 10))
    q = request.args.get("q")

    query = db.session.query(Workspace)
    if q:
        query = query.filter(Workspace.id.like(f"{q}%") | Workspace.name.like(f"{q}%"))

    total = query.count()
    workspaces = query.limit(size).offset((page - 1) * size).all()

    return BaseResult(data=[workspace.to_dict() for workspace in workspaces]).response(
        total
    )


@bp.route(rule="/api/admin/workspace/v1", methods=["POST"])
@auth_required(module=PermissionModule.WORKSPACE_MANAGE.name, actions=["CREATE"])
def create_workspace():
    data = ApiWorkspaceSchema().load(request.get_json())
    _exists = db.session.query(Workspace).filter_by(name=data["name"]).first()
    if _exists:
        return make_response("Workspace name alredy exists", 401)
    workspace = Workspace(**data)
    db.session.add(workspace)
    db.session.commit()
    return BaseResult().response()


@bp.route(rule="/api/admin/workspace/v1", methods=["PUT"])
@auth_required(module=PermissionModule.WORKSPACE_MANAGE.name, actions=["EDIT"])
def edit_workspace():
    data = ApiWorkspaceSchema().load(request.get_json())
    _exists = db.session.query(Workspace).filter_by(id=data["id"]).first()
    if not _exists:
        return make_response("Workspace does't exists", 401)
    _exists.name = data["name"]
    _exists.description = data["description"]
    db.session.commit()
    return BaseResult().response()


@bp.route(rule="/api/admin/workspace/v1", methods=["DELETE"])
@auth_required(module=PermissionModule.WORKSPACE_MANAGE.name, actions=["DELETE"])
def delete_workspace():
    workspace_id = request.args["id"]
    workspace = db.session.query(Workspace).filter_by(id=workspace_id).first()
    workers = db.session.query(Worker).filter(Worker.workspace_id == workspace_id).all()
    worker_ids = [worker.id for worker in workers]
    managed_objects = (
        db.session.query(ManagedObjects)
        .filter(ManagedObjects.worker_id.in_(worker_ids))
        .all()
    )
    managed_object_ids = [managed_object.id for managed_object in managed_objects]

    db.session.query(GroupPermission).filter(
        GroupPermission.source_id.in_(managed_object_ids),
        GroupPermission.type == "OBJECT",
    ).delete()

    db.session.query(GroupPermission).filter(
        GroupPermission.source_id.in_(worker_ids),
        GroupPermission.type == constants.PermissionType.WORKER.name,
    ).delete()

    db.session.query(GroupPermission).filter(
        GroupPermission.source_id == workspace_id,
        GroupPermission.type == constants.PermissionType.WORKSPACE.name,
    ).delete()

    for managed_object in managed_objects:
        db.session.delete(managed_object)

    for worker in workers:
        db.session.delete(worker)

    db.session.delete(workspace)
    db.session.commit()
    return BaseResult().response()


@bp.route(rule="/api/admin/workspace/permission/v1", methods=["GET"])
@auth_required(module=PermissionModule.WORKSPACE_MANAGE.name, actions=["PERMISSION"])
def get_workspace_permission():
    workspace = (
        db.session.query(Workspace).filter(Workspace.id == request.args["id"]).first()
    )
    groups = db.session.query(Group).all()
    group_permissions = (
        db.session.query(GroupPermission)
        .filter(
            GroupPermission.source_id == workspace.id,
            GroupPermission.type == constants.PermissionType.WORKSPACE.name,
        )
        .all()
    )
    result = []
    for group in groups:
        permissions = [
            group_permission.permission
            for group_permission in group_permissions
            if group_permission.group_id == group.id
        ]
        result.append(
            {"group_id": group.id, "group_name": group.name, "permissions": permissions}
        )
    return BaseResult(data=result).response()


@bp.route(rule="/api/admin/workspace/permission/v1", methods=["PUT"])
@auth_required(module=PermissionModule.WORKSPACE_MANAGE.name, actions=["PERMISSION"])
def edit_workspace_permission():
    data = request.get_json()
    workspace = (
        db.session.query(Workspace).filter(Workspace.id == request.args["id"]).first()
    )

    add_group_permission_list = []
    db.session.query(GroupPermission).filter(
        GroupPermission.source_id == workspace.id,
        GroupPermission.type == constants.PermissionType.WORKSPACE.name,
    ).delete()

    for _group_permissions in data:
        group_id = _group_permissions["group_id"]
        permissions = _group_permissions["permissions"]
        for permission in permissions:
            add_group_permission_list.append(
                GroupPermission(
                    source_id=workspace.id,
                    type=constants.PermissionType.WORKSPACE.name,
                    permission=permission,
                    group_id=group_id,
                )
            )
    db.session.add_all(add_group_permission_list)
    db.session.commit()
    return BaseResult().response()


@bp.route(rule="/api/admin/worker/v1", methods=["GET"])
@auth_required(module=PermissionModule.WORKSPACE_WORKER_MANAGE.name, actions=["READ"])
def read_worker():
    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 10))
    workspace_id = request.headers.get(constants.X_WORKSPACE)
    q = request.args.get("q", "")
    controller_ns = current_app.config.get(CONTROLLER_NAMESPACE)

    query = db.session.query(Worker)
    if q:
        query = query.filter(
            Worker.workspace_id
            == workspace_id & (Worker.id.like(f"%{q}%") | Worker.name.like(f"%{q}%"))
        )
    else:
        query = query.filter(Worker.workspace_id == workspace_id)

    total = query.count()
    workers = query.limit(size).offset((page - 1) * size).all()

    resp_data = []
    for worker in workers:
        worker_dict = worker.to_dict()
        worker_dict["online"] = (
            True if controller_ns.is_worker_online(worker.id) else False
        )
        worker_dict.pop("secret")
        resp_data.append(worker_dict)

    return BaseResult(data=resp_data).response(total)


@bp.route(rule="/api/admin/worker/v1", methods=["POST"])
@auth_required(module=PermissionModule.WORKSPACE_WORKER_MANAGE.name, actions=["CREATE"])
def create_worker():
    workspace_id = request.headers[constants.X_WORKSPACE]
    data = ApiWorkspaceSchema().load(request.get_json())
    _exists = db.session.query(Worker).filter_by(name=data["name"]).first()
    if _exists:
        return make_response("Agent name alredy exists", 401)
    token = secrets.token_urlsafe(32)
    worker = Worker(
        workspace_id=workspace_id,
        name=data["name"],
        description=data.get("description", ""),
        secret=token,
    )
    db.session.add(worker)
    db.session.commit()
    return BaseResult().response()


@bp.route(rule="/api/admin/worker/v1", methods=["PUT"])
@auth_required(module=PermissionModule.WORKSPACE_WORKER_MANAGE.name, actions=["EDIT"])
def edit_worker():
    workspace_id = request.headers[constants.X_WORKSPACE]
    data = ApiWorkspaceSchema().load(request.get_json())
    _exists = db.session.query(Worker).filter_by(id=data["id"]).first()
    if not _exists:
        return make_response("Worker does't exists", 401)
    if workspace_id != _exists.workspace_id:
        return make_response("Workerspace error", 401)
    _exists.name = data["name"]
    _exists.description = data.get("description", "")
    db.session.commit()
    return BaseResult().response()


@bp.route(rule="/api/admin/worker/v1", methods=["DELETE"])
@auth_required(module=PermissionModule.WORKSPACE_WORKER_MANAGE.name, actions=["DELETE"])
def delete_worker():
    worker_id = request.args["id"]
    workspace_id = request.headers[constants.X_WORKSPACE]
    worker = db.session.query(Worker).filter_by(id=worker_id).first()
    if not worker:
        return make_response("Worker does't exists", 401)
    if workspace_id != worker.workspace_id:
        return make_response("Workerspace error", 401)

    managed_objects = (
        db.session.query(ManagedObjects)
        .filter(ManagedObjects.worker_id == worker_id)
        .all()
    )
    managed_object_ids = [managed_object.id for managed_object in managed_objects]

    db.session.query(GroupPermission).filter(
        GroupPermission.source_id.in_(managed_object_ids),
        GroupPermission.type == "OBJECT",
    ).delete()

    db.session.query(GroupPermission).filter(
        GroupPermission.source_id == worker_id,
        GroupPermission.type == constants.PermissionType.WORKER.name,
    ).delete()

    for managed_object in managed_objects:
        db.session.delete(managed_object)

    db.session.delete(worker)
    db.session.commit()
    return BaseResult().response()


@bp.route(rule="/api/admin/worker/detail/v1", methods=["GET"])
@auth_required(module=PermissionModule.WORKSPACE_WORKER_MANAGE.name, actions=["DETAIL"])
def get_worker_detail():
    worker_id = request.args["id"]
    workspace_id = request.headers[constants.X_WORKSPACE]
    worker = db.session.query(Worker).filter_by(id=worker_id).first()
    if not worker:
        return make_response("Worker does't exists", 401)
    if workspace_id != worker.workspace_id:
        return make_response("Workerspace error", 401)
    return BaseResult(data=worker.to_dict()).response()


@bp.route(rule="/api/admin/managed_object/v1", methods=["GET"])
@auth_required(
    module=PermissionModule.WORKER_MANAGED_OBJECT_MANAGE.name, actions=["READ"]
)
def get_managed_object():
    page = int(request.args.get("page", 1))
    size = int(request.args.get("size", 10))
    q = request.args.get("q")
    workspace_id = request.headers[constants.X_WORKSPACE]
    conditions = [Worker.workspace_id == workspace_id]
    if q:
        conditions.append(
            sqlalchemy.or_(
                ManagedObjects.system_id.like(f"%{q}%"),
                ManagedObjects.system_type.like(f"%{q}%"),
                Worker.name.like(f"%{q}%"),
            )
        )
    stmt = (
        sqlalchemy.select(
            ManagedObjects.id,
            ManagedObjects.system_id,
            ManagedObjects.system_type,
            ManagedObjects.url,
            ManagedObjects.worker_id,
            Worker.name.label("worker_name"),
        )
        .join(Worker, ManagedObjects.worker_id == Worker.id)
        .where(*conditions)
    )
    items, total = paginate(stmt, page, size)

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

    return BaseResult(data=data).response(total)


@bp.route(rule="/api/admin/managed_object/permission/v1", methods=["GET"])
@auth_required(
    module=PermissionModule.MANAGED_OBJECT_PERMISSION_MANAGE.name,
    actions=["READ"],
)
def get_managed_object_permission():
    managed_object = (
        db.session.query(ManagedObjects)
        .filter(ManagedObjects.id == request.args["id"])
        .first()
    )
    groups = db.session.query(Group).all()
    group_permissions = (
        db.session.query(GroupPermission)
        .filter(
            GroupPermission.source_id == managed_object.id,
            GroupPermission.type == constants.PermissionType.OBJECT.name,
        )
        .all()
    )
    result = []
    for group in groups:
        permissions = [
            group_permission.permission
            for group_permission in group_permissions
            if group_permission.group_id == group.id
        ]
        result.append(
            {"group_id": group.id, "group_name": group.name, "permissions": permissions}
        )
    return BaseResult(data=result).response()


@bp.route(rule="/api/admin/managed_object/permission/v1", methods=["PUT"])
@auth_required(
    module=PermissionModule.MANAGED_OBJECT_PERMISSION_MANAGE.name,
    actions=["EDIT"],
)
def edit_managed_object_permission():
    data = request.get_json()
    managed_object = (
        db.session.query(ManagedObjects)
        .filter(ManagedObjects.id == request.args["id"])
        .first()
    )

    add_group_permission_list = []
    db.session.query(GroupPermission).filter(
        GroupPermission.source_id == managed_object.id,
        GroupPermission.type == constants.PermissionType.OBJECT.name,
    ).delete()

    for _group_permissions in data:
        group_id = _group_permissions["group_id"]
        permissions = _group_permissions["permissions"]
        for permission in permissions:
            add_group_permission_list.append(
                GroupPermission(
                    source_id=managed_object.id,
                    type=constants.PermissionType.OBJECT.name,
                    permission=permission,
                    group_id=group_id,
                )
            )
    db.session.add_all(add_group_permission_list)
    db.session.commit()
    return BaseResult().response()
