from flask import Flask, Blueprint, session, current_app, make_response
from flask_session import Session
from authlib.integrations.flask_client import OAuth
from configops.config import get_auth_config, get_config
from configops import config as configops_config
from configops.api.utils import BaseResult, auth_required
from configops.utils.constants import PermissionType
from configops.database.db import db, User, UserGroup, Group, GroupPermission, Workspace
import logging, time, os
from redis import Redis
import sqlalchemy


logger = logging.getLogger(__name__)
bp = Blueprint("auth", __name__)

UNAUTHORIZED_ACTION_MESSAGE = "You are not authorized to perform this action."
oauth = OAuth()
EXT_CONFIG_OPS_OIDC_NAME = "configops.auth.oidc"


def __get_oidc_config(app: Flask):
    auth_config = get_auth_config(app)
    if not auth_config or not auth_config.get("oidc"):
        return None
    oidc_config = auth_config["oidc"]
    return oidc_config


def init_app(app: Flask):
    app.secret_key = "Y7r/BnzmlNCurDns7wDQLNJBQ6eqF3UuvS3f7L01iAI3SZr6oiUlPX5H"

    redis_uri = get_config(app, "config.redis_uri")
    if not redis_uri:
        redis_uri = os.getenv("SQLALCHEMY_DATABASE_URI")

    app.config["SESSION_KEY_PREFIX"] = "configops_session:"
    if redis_uri:
        app.config["SESSION_TYPE"] = "redis"
        app.config["SESSION_REDIS"] = Redis.from_url(redis_uri)
    else:
        app.config["SESSION_TYPE"] = "sqlalchemy"
        app.config["SESSION_SQLALCHEMY_TABLE"] = "configops_sessions"
        app.config["SESSION_SQLALCHEMY"] = app.extensions["sqlalchemy"]

    Session(app)

    oidc_config = __get_oidc_config(app)
    if oidc_config and oidc_config.get("enabled", False):
        oauth.init_app(app)
        oidc = oauth.register(
            name="oidc",
            client_id=oidc_config["client_id"],
            client_secret=oidc_config["client_secret"],
            server_metadata_url=f"{oidc_config['issuer']}/.well-known/openid-configuration",
            client_kwargs={"scope": oidc_config["scope"]},
        )
        app.extensions[EXT_CONFIG_OPS_OIDC_NAME] = oidc


# WHITELIST_ROUTES = ['/public', '/healthcheck']


@bp.route("/api/oidc/info", methods=["GET"])
def oidc_info():
    oidc = current_app.extensions.get(EXT_CONFIG_OPS_OIDC_NAME)
    if oidc:
        oidc_config = __get_oidc_config(current_app)
        auto_login = oidc_config.get("auto_login", False)
        login_txt = oidc_config.get("login_txt", "Signin with OIDC")
        return BaseResult(
            data={
                "enabled": True,
                "auto_login": auto_login,
                "login_txt": login_txt,
                "sso_url": "/api/oidc/login",
            }
        ).response()
    else:
        return BaseResult(data={"enabled": False}).response()


@bp.route("/api/oidc/login", methods=["GET"])
def oidc_login():
    oidc = current_app.extensions.get(EXT_CONFIG_OPS_OIDC_NAME)
    home_url = configops_config.get_config(current_app, "config.home_url")
    return oidc.authorize_redirect(f"{home_url}/oidc/callback")


@bp.route("/api/oidc/callback", methods=["GET", "POST"])
def oidc_callback():
    oidc = current_app.extensions.get(EXT_CONFIG_OPS_OIDC_NAME)
    oidc_config = __get_oidc_config(current_app)
    try:
        token = oidc.authorize_access_token()
    except Exception as e:
        logger.error(f"OIDC authorize_access_token error: {e}")
        return make_response("Please relogin", 401)

    userinfo = token["userinfo"]
    user_id = userinfo["sub"]
    name = userinfo.get("name", userinfo.get("nickname", user_id))
    user = db.session.query(User).filter_by(id=user_id).first()
    if not user:
        user = User(
            id=user_id,
            name=name,
            email=userinfo["email"],
            source="oidc",
            status="NORMAL",
        )
        db.session.add(user)
    else:
        user.name = name
        user.email = userinfo["email"]

    groups_sync = oidc_config.get("groups_sync")

    if groups_sync:
        oidc_groups = userinfo[groups_sync]
        groups = db.session.query(Group).filter(Group.id.in_(oidc_groups)).all()
        for group in groups:
            user_group = (
                db.session.query(UserGroup)
                .filter(UserGroup.user_id == user.id, UserGroup.group_id == group.id)
                .first()
            )
            if not user_group:
                user_group = UserGroup(user_id=user.id, group_id=group.id)
                db.session.add(user_group)
    db.session.commit()

    permissions = []
    groups = []

    user_groups = db.session.query(UserGroup).filter(UserGroup.user_id == user.id).all()
    if user_groups and len(user_groups) > 0:
        groups = [user_group.group_id for user_group in user_groups]
        stmt = (
            sqlalchemy.select(
                GroupPermission.group_id,
                GroupPermission.source_id,
                GroupPermission.type,
                GroupPermission.permission,
            )
            .join(UserGroup, UserGroup.group_id == GroupPermission.group_id)
            .where(
                UserGroup.group_id.in_(groups),
                GroupPermission.type != PermissionType.WEB_MENU.name,
            )
        )
        group_permissions = db.session.execute(stmt).all()
        permissions = [
            {
                "group_id": item.group_id,
                "source_id": item.source_id,
                "type": item.type,
                "permission": item.permission,
            }
            for item in group_permissions
        ]

    session["userinfo"] = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "source": user.source,
    }
    session["permissions"] = permissions
    session["groups"] = groups
    return BaseResult(data={"id": user.id, "name": user.name}).response()


@bp.route("/api/user/logout", methods=["DELETE"])
@auth_required()
def logout():
    session.clear()
    return BaseResult().response()


@bp.route("/api/userinfo", methods=["GET"])
@auth_required()
def userinfo():
    userinfo = session["userinfo"]
    return BaseResult(data=userinfo).response()


def __get_sources_ids(groups: list, permission_type: PermissionType):
    source_ids = []
    if groups and len(groups) > 0:
        group_permissions = (
            db.session.query(GroupPermission)
            .filter(
                GroupPermission.group_id.in_(groups),
                GroupPermission.type == permission_type.name,
            )
            .all()
        )
        source_ids = [item.source_id for item in group_permissions]
    return source_ids


@bp.route("/api/user/menus", methods=["GET"])
@auth_required()
def get_user_menus():
    groups = session["groups"]
    menus = __get_sources_ids(groups, PermissionType.WEB_MENU)
    return BaseResult(data=menus).response()


@bp.route("/api/user/workspaces", methods=["GET"])
@auth_required()
def get_workspaces():
    groups = session["groups"]
    workspaces = []
    workspace_ids = __get_sources_ids(groups, PermissionType.WORKSPACE)
    if len(workspace_ids) > 0:
        workspaces = (
            db.session.query(Workspace).filter(Workspace.id.in_(workspace_ids)).all()
        )
    return BaseResult(data=[item.to_dict() for item in workspaces]).response()
