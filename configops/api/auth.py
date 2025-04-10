from flask import (
    Flask,
    Blueprint,
    redirect,
    request,
    session,
    current_app,
    jsonify,
    render_template,
)
from flask_session import Session
from authlib.integrations.flask_client import OAuth
from authlib.jose import jwt
from functools import wraps
from configops.config import get_auth_config
from configops import config as configops_config
import os
import logging
import time
from configops.database.db import db, User, UserGroup

logger = logging.getLogger(__name__)
bp = Blueprint("auth", __name__)
oauth = OAuth()
EXT_CONFIG_OPS_OIDC_NAME = "configops.auth.oidc"


def __get_oidc_config(app: Flask):
    auth_config = get_auth_config(app)
    if not auth_config or not auth_config.get("oidc"):
        return None
    oidc_config = auth_config["oidc"]
    return oidc_config


def init_app(app: Flask):
    app.secret_key = os.urandom(24)
    app.config["SESSION_TYPE"] = "filesystem"
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


# 鉴权装饰器（支持白名单和 SAML 认证）
def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # if request.path in WHITELIST_ROUTES:
        #    return f(*args, **kwargs)  # 白名单直接放行

        if "userinfo" not in session:
            return redirect("/oidc/login")  # 未登录跳转 SAML 登录

        # 可选：检查用户角色（从 SAML 属性中获取）
        user_roles = session.get("samlUserdata", {}).get("Role", [])
        if "admin" not in user_roles:  # 假设需要 admin 角色
            return jsonify({"error": "Forbidden"}), 403

        return f(*args, **kwargs)

    return decorated


@bp.route("/oidc/login")
def oidc_login():
    oidc = current_app.extensions.get(EXT_CONFIG_OPS_OIDC_NAME)
    home_url = configops_config.get_config(current_app, "config.home_url")
    return oidc.authorize_redirect(f"{home_url}/oidc/callback")


@bp.route("/oidc/callback")
def oidc_callback():
    oidc = current_app.extensions[EXT_CONFIG_OPS_OIDC_NAME]
    token = oidc.authorize_access_token()
    userinfo = token["userinfo"]
    user_id = userinfo["sub"]
    user = db.session.query(User).filter_by(id=user_id).first()
    if not user:
        user = User(id=user_id, email=userinfo["email"], source="oidc", status="NORMAL")
        db.session.add(user)
        db.session.commit()
    else:
        user.email = userinfo["email"]
        db.session.commit()

    # 用户组映射

    session["userinfo"] = userinfo
    session["access_token"] = token["access_token"]
    session["refresh_token"] = token.get("refresh_token")
    session["expires_at"] = time.time() + token["expires_in"]
    return redirect("/")


@bp.route("/userinfo")
@auth_required
def user_info():
    """
    获取用户信息
    """
    if "samlUserdata" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_data = session["samlUserdata"]
    return jsonify(user_data)
