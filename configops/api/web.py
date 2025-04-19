# flask-backend/app.py
from flask import Blueprint, send_from_directory, current_app
import logging, os

logger = logging.getLogger(__name__)

bp = Blueprint("web", __name__, url_prefix=os.getenv("FLASK_APPLICATION_ROOT", "/"))


@bp.route("/")
def index():
    return send_from_directory(
        current_app.static_folder, __static_file_path("index.html")
    )


@bp.route("/<path:path>")
def static_proxy(path):
    if "." in path:
        return send_from_directory(current_app.static_folder, __static_file_path(path))
    else:
        return send_from_directory(
            current_app.static_folder, __static_file_path("index.html")
        )


def __static_file_path(path):
    application_root = current_app.config.get("APPLICATION_ROOT", "/")
    if application_root.startswith("/"):
        application_root = application_root[1:]
    if application_root:
        return f"{application_root}/{path}"
    else:
        return path
