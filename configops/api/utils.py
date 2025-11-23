from flask import request, session, make_response, jsonify
from http import HTTPStatus
from functools import wraps
from configops.utils.constants import (
    PermissionType,
    PermissionModule,
    X_WORKSPACE,
)
from typing import Optional, Union

RESP_OK = 0
RESP_ERROR = -1


def __check_permission__(
    permission,
    module: PermissionModule,
    actions,
    workspace_id=None,
    managed_object_id=None,
):
    _type = permission.get("type")
    _source_id = permission.get("source_id")

    if (
        module.check_workspace(module.name)
        and _type == PermissionType.WORKSPACE.name
        and _source_id != workspace_id
    ) or (
        module.check_object(module.name)
        and _type == PermissionType.OBJECT.name
        and _source_id != managed_object_id
    ):
        return False

    _module_actions = permission.get("permission").split(":")
    if _module_actions[0] != module.name:
        return False
    _actions = _module_actions[1].split("+")
    if "ALL" in _actions or set(actions).issubset(set(_actions)):
        return True


def do_check_auth(
    module: Optional[Union[str, PermissionModule]] = None,
    actions: Optional[list] = None,
):
    if "userinfo" not in session:
        return make_response("You are not logged in.", 401)

    if not module or not actions:
        return None

    if isinstance(module, str):
        permission_module = PermissionModule[module]
    else:
        permission_module = module

    user_permissions = session["permissions"]
    workspace_id = request.headers.get(X_WORKSPACE, "")
    managed_object_id = request.args.get("managed_object_id", "")

    for permission in user_permissions:
        if __check_permission__(
            permission, permission_module, actions, workspace_id, managed_object_id
        ):
            return None

    return make_response("You do not have permission to perform this action.", 403)


def auth_required(
    module: Optional[Union[str, PermissionModule]] = None,
    actions: Optional[list] = None,
):
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            resp = do_check_auth(module, actions)
            if resp:
                return resp
            return func(*args, **kwargs)

        return wrapper

    return decorate


class BaseResult:
    """A class to represent a JSON response."""

    def __init__(
        self,
        code: int = RESP_OK,
        status: HTTPStatus = HTTPStatus.OK,
        msg: str = "success",
        data=None,
    ):
        self.code = code
        self.status = status
        self.msg = msg
        self.data = data
        self.page_total = None

    def to_dict(self):
        resp_dict = {
            "code": self.code,
            "msg": self.msg,
            "data": self.data,
        }
        if self.page_total:
            resp_dict["total"] = self.page_total
        return resp_dict

    def to_json(self):
        return jsonify(self.to_dict())

    def response(self, total=None):
        self.page_total = total
        response = make_response(self.to_json(), self.status.value)
        response.headers["Content-Type"] = "application/json"
        return response

    @staticmethod
    def error(msg: str = None):
        return BaseResult(code=RESP_ERROR, msg=msg)

    @staticmethod
    def ok(data=None, total=None):
        result = BaseResult(data=data)
        result.page_total = total
        return result
